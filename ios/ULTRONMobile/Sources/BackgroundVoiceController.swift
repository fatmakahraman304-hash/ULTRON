import Foundation
import AVFoundation
import SwiftUI
import UIKit

@MainActor
final class BackgroundVoiceController: ObservableObject {
    static let shared = BackgroundVoiceController()

    @Published var listening = false
    @Published var connected = false
    @Published var desiredListening = false
    @Published var status = "Hazır"
    @Published var lastTranscript = ""
    @Published var needsLogin = false
    @Published var reconnectAttempt = 0
    @Published var isBackground = false

    private let audioEngine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var socket: URLSessionWebSocketTask?
    private var converter: AVAudioConverter?
    private var inputTapInstalled = false
    private var reconnectTask: Task<Void, Never>?
    private var heartbeatTask: Task<Void, Never>?
    private var pingTask: Task<Void, Never>?
    private var observers: [NSObjectProtocol] = []

    private let outputFormat = AVAudioFormat(
        commonFormat: .pcmFormatFloat32,
        sampleRate: 24_000,
        channels: 1,
        interleaved: false
    )!

    private var sessionID: String {
        let key = "ultron.native.live.session"
        if let existing = UserDefaults.standard.string(forKey: key), !existing.isEmpty {
            return existing
        }
        let value = UUID().uuidString
        UserDefaults.standard.set(value, forKey: key)
        return value
    }

    private init() {
        audioEngine.attach(player)
        audioEngine.connect(player, to: audioEngine.mainMixerNode, format: outputFormat)
        installAudioObservers()
        PhoneActionRouter.shared.requestNotificationPermission()
    }

    func configureAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [.allowBluetooth, .defaultToSpeaker]
            )
            try session.setPreferredSampleRate(48_000)
            try session.setPreferredIOBufferDuration(0.02)
            try session.setActive(true)
        } catch {
            status = "Ses oturumu başlatılamadı: \(error.localizedDescription)"
        }
    }

    func login(password: String) async {
        do {
            try await CloudSession.shared.login(password: password)
            needsLogin = false
            status = "Cloud bağlı"
        } catch {
            needsLogin = true
            status = "Giriş başarısız"
        }
    }

    func start() async {
        guard !desiredListening else { return }

        desiredListening = true
        reconnectAttempt = 0
        status = "Mikrofon hazırlanıyor…"

        let granted = await requestMicrophonePermission()
        guard granted else {
            desiredListening = false
            needsLogin = false
            status = "Mikrofon izni gerekli"
            return
        }

        configureAudioSession()

        do {
            try startAudioIfNeeded()
            listening = true
            startHeartbeatLoop()
            await connectSocket()
        } catch {
            desiredListening = false
            listening = false
            status = "Ses başlatılamadı: \(error.localizedDescription)"
            stopAudio()
        }
    }

    func stop() async {
        desiredListening = false
        connected = false
        listening = false
        reconnectAttempt = 0

        reconnectTask?.cancel()
        reconnectTask = nil
        heartbeatTask?.cancel()
        heartbeatTask = nil
        pingTask?.cancel()
        pingTask = nil

        socket?.cancel(with: .normalClosure, reason: nil)
        socket = nil

        stopAudio()
        status = "Durduruldu"
    }

    func handleScenePhase(_ phase: ScenePhase) {
        switch phase {
        case .active:
            isBackground = false
            PhoneActionRouter.shared.resumePendingActionIfPossible()
            if desiredListening {
                status = connected ? "Sürekli dinleme aktif" : "Cloud'a yeniden bağlanıyor…"
                if !connected {
                    scheduleReconnect(immediate: true)
                }
            }

        case .background:
            isBackground = true
            if desiredListening {
                status = "Arka planda dinliyor"
            }

        case .inactive:
            break

        @unknown default:
            break
        }
    }

    private func requestMicrophonePermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    private func startAudioIfNeeded() throws {
        if !inputTapInstalled {
            try installInputTap()
        }

        if !audioEngine.isRunning {
            audioEngine.prepare()
            try audioEngine.start()
        }

        if !player.isPlaying {
            player.play()
        }
    }

    private func stopAudio() {
        if inputTapInstalled {
            audioEngine.inputNode.removeTap(onBus: 0)
            inputTapInstalled = false
        }
        if audioEngine.isRunning {
            audioEngine.stop()
        }
        player.stop()
        converter = nil
    }

    private func connectSocket() async {
        guard desiredListening else { return }

        do {
            try await CloudSession.shared.ensureLogin()
            needsLogin = false

            socket?.cancel(with: .goingAway, reason: nil)
            let task = await CloudSession.shared.webSocketTask(sessionID: sessionID)
            socket = task
            task.resume()

            connected = true
            reconnectAttempt = 0
            status = isBackground ? "Arka planda dinliyor" : "Cloud Live bağlı • sürekli dinliyor"
            receiveLoop(task)
            startPingLoop(task)
        } catch {
            connected = false
            if case URLError.userAuthenticationRequired = error {
                needsLogin = true
                status = "Önce Cloud girişi gerekli"
            } else {
                status = "Cloud bağlantısı bekleniyor…"
                scheduleReconnect()
            }
        }
    }

    private func scheduleReconnect(immediate: Bool = false) {
        guard desiredListening else { return }
        guard reconnectTask == nil else { return }

        reconnectAttempt = min(reconnectAttempt + 1, 8)
        let delay: Double = immediate ? 0.15 : min(15.0, 0.8 * pow(1.8, Double(reconnectAttempt - 1)))

        reconnectTask = Task { [weak self] in
            guard let self else { return }
            try? await Task.sleep(for: .seconds(delay))
            guard !Task.isCancelled, self.desiredListening else {
                self.reconnectTask = nil
                return
            }

            self.reconnectTask = nil
            await self.connectSocket()
        }
    }

    private func startHeartbeatLoop() {
        heartbeatTask?.cancel()
        heartbeatTask = Task { [weak self] in
            guard let self else { return }

            while !Task.isCancelled, self.desiredListening {
                await CloudSession.shared.heartbeat(state: [
                    "native_ios": true,
                    "voice_listening": self.listening,
                    "voice_connected": self.connected,
                    "background": self.isBackground,
                    "session_id": self.sessionID
                ])
                try? await Task.sleep(for: .seconds(10))
            }
        }
    }

    private func startPingLoop(_ task: URLSessionWebSocketTask) {
        pingTask?.cancel()
        pingTask = Task { [weak self, weak task] in
            guard let self, let task else { return }

            while !Task.isCancelled, self.desiredListening, self.socket === task {
                try? await Task.sleep(for: .seconds(20))
                guard !Task.isCancelled, self.desiredListening, self.socket === task else { return }

                task.sendPing { error in
                    if let error {
                        Task { @MainActor [weak self] in
                            self?.socketFailed(error, task: task)
                        }
                    }
                }
            }
        }
    }

    private func installInputTap() throws {
        let input = audioEngine.inputNode
        let format = input.inputFormat(forBus: 0)

        guard let target = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16_000,
            channels: 1,
            interleaved: true
        ) else {
            throw NSError(domain: "ULTRON", code: 1)
        }

        guard let converter = AVAudioConverter(from: format, to: target) else {
            throw NSError(domain: "ULTRON", code: 2)
        }
        self.converter = converter

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 2048, format: format) { [weak self] buffer, _ in
            guard let self else { return }
            Task { @MainActor in
                self.convertAndSend(buffer, targetFormat: target)
            }
        }
        inputTapInstalled = true
    }

    private func convertAndSend(_ buffer: AVAudioPCMBuffer, targetFormat: AVAudioFormat) {
        guard desiredListening, connected, let converter, let socket else { return }

        let ratio = targetFormat.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 64
        guard let out = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: capacity) else { return }

        var supplied = false
        var error: NSError?
        converter.convert(to: out, error: &error) { _, status in
            if supplied {
                status.pointee = .noDataNow
                return nil
            }
            supplied = true
            status.pointee = .haveData
            return buffer
        }

        guard error == nil,
              out.frameLength > 0,
              let data = out.audioBufferList.pointee.mBuffers.mData else { return }

        let byteCount = Int(out.frameLength) * Int(targetFormat.streamDescription.pointee.mBytesPerFrame)
        let pcm = Data(bytes: data, count: byteCount)

        socket.send(.data(pcm)) { [weak self, weak socket] error in
            guard let error, let socket else { return }
            Task { @MainActor in
                self?.socketFailed(error, task: socket)
            }
        }
    }

    private func receiveLoop(_ task: URLSessionWebSocketTask) {
        task.receive { [weak self, weak task] result in
            guard let self, let task else { return }

            Task { @MainActor in
                guard self.socket === task, self.desiredListening else { return }

                switch result {
                case .failure(let error):
                    self.socketFailed(error, task: task)

                case .success(let message):
                    switch message {
                    case .data(let data):
                        self.playPCM24k(data)

                    case .string(let string):
                        self.handleEvent(string)

                    @unknown default:
                        break
                    }

                    if self.socket === task, self.desiredListening {
                        self.receiveLoop(task)
                    }
                }
            }
        }
    }

    private func socketFailed(_ error: Error, task: URLSessionWebSocketTask) {
        guard socket === task, desiredListening else { return }

        connected = false
        task.cancel(with: .goingAway, reason: nil)
        socket = nil
        status = "Bağlantı yenileniyor…"
        scheduleReconnect()
    }

    private func handleEvent(_ string: String) {
        guard let data = string.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = obj["type"] as? String else { return }

        switch type {
        case "ready":
            connected = true
            status = isBackground ? "Arka planda dinliyor" : "Cloud Live bağlı • sürekli dinliyor"

        case "input_transcript":
            if let text = obj["text"] as? String {
                lastTranscript = text
                status = "Sen: \(text)"
            }

        case "output_transcript":
            status = "ULTRON konuşuyor"

        case "turn_complete":
            status = isBackground ? "Arka planda dinliyor" : "Sürekli dinleme aktif"

        case "phone_action":
            let action = (obj["action"] as? String) ?? ""
            let query = (obj["query"] as? String) ?? ""
            PhoneActionRouter.shared.handle(action: action, query: query)

        case "error":
            status = (obj["message"] as? String) ?? "Cloud Live hatası"

        default:
            break
        }
    }

    private func playPCM24k(_ data: Data) {
        let frames = AVAudioFrameCount(data.count / 2)
        guard frames > 0,
              let buffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: frames),
              let channel = buffer.floatChannelData?[0] else { return }

        buffer.frameLength = frames
        data.withUnsafeBytes { raw in
            guard let src = raw.bindMemory(to: Int16.self).baseAddress else { return }
            for i in 0..<Int(frames) {
                channel[i] = Float(src[i]) / 32768.0
            }
        }

        player.scheduleBuffer(buffer)
        if !player.isPlaying {
            player.play()
        }
    }

    private func installAudioObservers() {
        let center = NotificationCenter.default

        observers.append(
            center.addObserver(
                forName: AVAudioSession.interruptionNotification,
                object: AVAudioSession.sharedInstance(),
                queue: .main
            ) { [weak self] note in
                Task { @MainActor in
                    self?.handleAudioInterruption(note)
                }
            }
        )

        observers.append(
            center.addObserver(
                forName: AVAudioSession.routeChangeNotification,
                object: AVAudioSession.sharedInstance(),
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor in
                    guard let self, self.desiredListening else { return }
                    self.configureAudioSession()
                    if !self.audioEngine.isRunning {
                        try? self.startAudioIfNeeded()
                    }
                }
            }
        )
    }

    private func handleAudioInterruption(_ note: Notification) {
        guard let info = note.userInfo,
              let rawType = info[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: rawType) else { return }

        switch type {
        case .began:
            status = "Ses geçici olarak duraklatıldı"

        case .ended:
            guard desiredListening else { return }
            configureAudioSession()
            do {
                try startAudioIfNeeded()
                listening = true
                if !connected {
                    scheduleReconnect(immediate: true)
                }
            } catch {
                status = "Ses yeniden başlatılamadı"
            }

        @unknown default:
            break
        }
    }
}
