import Foundation
import AVFoundation
import UIKit

@MainActor
final class BackgroundVoiceController: ObservableObject {
    @Published var listening = false
    @Published var status = "Hazır"
    @Published var lastTranscript = ""
    @Published var needsLogin = false

    private let audioEngine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var socket: URLSessionWebSocketTask?
    private var converter: AVAudioConverter?
    private var inputFormat: AVAudioFormat?
    private let outputFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                             sampleRate: 24_000,
                                             channels: 1,
                                             interleaved: false)!

    init() {
        audioEngine.attach(player)
        audioEngine.connect(player, to: audioEngine.mainMixerNode, format: outputFormat)
    }

    func configureAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [.allowBluetooth, .defaultToSpeaker, .mixWithOthers]
            )
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
        guard !listening else { return }
        configureAudioSession()

        do {
            try await CloudSession.shared.ensureLogin()
        } catch {
            needsLogin = true
            status = "Önce Cloud girişi gerekli"
            return
        }

        do {
            socket = await CloudSession.shared.webSocketTask()
            socket?.resume()
            try installInputTap()
            if !audioEngine.isRunning {
                try audioEngine.start()
            }
            if !player.isPlaying {
                player.play()
            }
            listening = true
            status = "Sürekli dinleme aktif"
            receiveLoop()
        } catch {
            status = "Ses başlatılamadı: \(error.localizedDescription)"
            await stop()
        }
    }

    func stop() async {
        listening = false
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        player.stop()
        socket?.cancel(with: .normalClosure, reason: nil)
        socket = nil
        status = "Durduruldu"
    }

    private func installInputTap() throws {
        let input = audioEngine.inputNode
        let format = input.inputFormat(forBus: 0)
        inputFormat = format

        guard let target = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16_000,
            channels: 1,
            interleaved: true
        ) else {
            throw NSError(domain: "ULTRON", code: 1)
        }

        converter = AVAudioConverter(from: format, to: target)

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 2048, format: format) { [weak self] buffer, _ in
            guard let self else { return }
            Task { @MainActor in
                self.convertAndSend(buffer, targetFormat: target)
            }
        }
    }

    private func convertAndSend(_ buffer: AVAudioPCMBuffer, targetFormat: AVAudioFormat) {
        guard let converter else { return }

        let ratio = targetFormat.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 32
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
        guard error == nil, out.frameLength > 0, let data = out.audioBufferList.pointee.mBuffers.mData else { return }

        let byteCount = Int(out.frameLength) * Int(targetFormat.streamDescription.pointee.mBytesPerFrame)
        let pcm = Data(bytes: data, count: byteCount)
        socket?.send(.data(pcm)) { _ in }
    }

    private func receiveLoop() {
        socket?.receive { [weak self] result in
            guard let self else { return }
            Task { @MainActor in
                switch result {
                case .failure(let error):
                    self.status = "Bağlantı kesildi: \(error.localizedDescription)"
                    self.listening = false
                case .success(let message):
                    switch message {
                    case .data(let data):
                        self.playPCM24k(data)
                    case .string(let string):
                        self.handleEvent(string)
                    @unknown default:
                        break
                    }
                    if self.listening {
                        self.receiveLoop()
                    }
                }
            }
        }
    }

    private func handleEvent(_ string: String) {
        guard let data = string.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = obj["type"] as? String else { return }

        switch type {
        case "ready":
            status = "Cloud Live bağlı • arka plan sesi aktif"
        case "input_transcript":
            if let text = obj["text"] as? String {
                lastTranscript = text
                status = "Sen: \(text)"
            }
        case "output_transcript":
            status = "ULTRON konuşuyor"
        case "phone_action":
            handlePhoneAction(obj)
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
        if !player.isPlaying { player.play() }
    }

    private func handlePhoneAction(_ obj: [String: Any]) {
        guard UIApplication.shared.applicationState == .active else {
            // iOS does not allow a background third-party app to foreground another app silently.
            status = "Komut alındı • uygulama açma için ULTRON'u öne getir"
            return
        }

        let action = (obj["action"] as? String) ?? ""
        let query = (obj["query"] as? String) ?? ""
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""

        let raw: String?
        switch action {
        case "open_app":
            raw = [
                "youtube": "youtube://",
                "spotify": "spotify://",
                "whatsapp": "whatsapp://",
                "instagram": "instagram://",
                "chrome": "googlechrome://"
            ][query.lowercased()]
        case "youtube_search":
            raw = "https://www.youtube.com/results?search_query=\(encoded)"
        case "spotify_search":
            raw = "https://open.spotify.com/search/\(encoded)"
        case "whatsapp_message":
            raw = "whatsapp://send?text=\(encoded)"
        case "maps":
            raw = "https://maps.apple.com/?q=\(encoded)"
        case "sms":
            raw = "sms:\(query)"
        case "email":
            raw = "mailto:\(query)"
        case "call":
            raw = "tel:\(query)"
        case "facetime":
            raw = "facetime:\(query)"
        default:
            raw = nil
        }

        guard let raw, let url = URL(string: raw) else { return }
        UIApplication.shared.open(url)
    }
}
