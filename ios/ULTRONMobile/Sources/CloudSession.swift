import Foundation

enum DesktopTaskError: LocalizedError {
    case invalidText, invalidResponse, notQueued

    var errorDescription: String? {
        switch self {
        case .invalidText: return "Görev 1–4000 karakter olmalı."
        case .invalidResponse: return "Cloud yanıtı doğrulanamadı."
        case .notQueued: return "Görev Cloud kuyruğuna alınamadı."
        }
    }
}

actor CloudSession {
    static let shared = CloudSession()

    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.httpCookieStorage = .shared
        config.httpShouldSetCookies = true
        config.waitsForConnectivity = true
        session = URLSession(configuration: config)
    }

    func login(password: String) async throws {
        var request = URLRequest(url: ULTRONConfig.baseURL.appending(path: "/api/login"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["password": password])

        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.userAuthenticationRequired)
        }

        KeychainStore.save(password, account: "cloud-password")
    }

    func ensureLogin() async throws {
        var request = URLRequest(url: ULTRONConfig.baseURL.appending(path: "/api/session"))
        request.httpMethod = "GET"

        do {
            let (_, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                return
            }
        } catch {
            // Retry below with the saved password when possible.
        }

        guard let password = KeychainStore.read(account: "cloud-password") else {
            throw URLError(.userAuthenticationRequired)
        }
        try await login(password: password)
    }

    /// Siri/App Shortcuts dispatch does not depend on a running microphone.
    /// The Cloud web session may enqueue a desktop task; risky laptop actions
    /// still require the local Approval Gate.
    func enqueueDesktopTask(_ text: String) async throws -> Int {
        let task = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !task.isEmpty, task.count <= 4_000 else {
            throw DesktopTaskError.invalidText
        }
        try await ensureLogin()
        var request = URLRequest(url: ULTRONConfig.baseURL.appending(path: "/api/device-commands"))
        request.httpMethod = "POST"
        request.timeoutInterval = 20
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("ultron-native-ios", forHTTPHeaderField: "X-ULTRON-DEVICE")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "target": "desktop", "command": "agent_task",
            "payload": ["text": task, "origin": "ios-shortcut"]
        ])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw DesktopTaskError.invalidResponse
        }
        if http.statusCode == 401 { throw URLError(.userAuthenticationRequired) }
        guard (200..<300).contains(http.statusCode),
              let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              body["ok"] as? Bool == true,
              let command = body["command"] as? [String: Any],
              let id = command["id"] as? Int, id > 0 else {
            throw DesktopTaskError.notQueued
        }
        return id
    }

    /// Siri answers short general questions from the shared Cloud brain.
    /// This is a bounded request; unlike Gemini Live it cannot dispatch
    /// device tools. Use enqueueDesktopTask for requested laptop actions.
    func askULTRON(_ question: String) async throws -> String {
        let message = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !message.isEmpty, message.count <= 2_000 else {
            throw DesktopTaskError.invalidText
        }
        try await ensureLogin()
        var request = URLRequest(url: ULTRONConfig.baseURL.appending(path: "/api/chat"))
        request.httpMethod = "POST"
        request.timeoutInterval = 45
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("ultron-native-ios", forHTTPHeaderField: "X-ULTRON-DEVICE")
        var body: [String: Any] = ["message": message]
        if let conversation = UserDefaults.standard.string(forKey: "ultron.siri.conversation_id"),
           !conversation.isEmpty {
            body["conversation_id"] = conversation
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse,
              http.statusCode == 200,
              let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let reply = result["reply"] as? String,
              !reply.isEmpty else {
            throw DesktopTaskError.invalidResponse
        }
        if let conversation = result["conversation_id"] as? String {
            UserDefaults.standard.set(conversation, forKey: "ultron.siri.conversation_id")
        }
        return reply
    }

    func webSocketTask(sessionID: String) -> URLSessionWebSocketTask {
        var components = URLComponents(url: ULTRONConfig.liveWebSocketURL, resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "session_id", value: sessionID)]
        return session.webSocketTask(with: components.url!)
    }

    func heartbeat(state: [String: Any]) async {
        do {
            var request = URLRequest(url: ULTRONConfig.baseURL.appending(path: "/api/device-presence/heartbeat"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("ultron-native-ios", forHTTPHeaderField: "X-ULTRON-DEVICE")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["state": state])
            _ = try await session.data(for: request)
        } catch {
            // Presence is best-effort and must never stop the voice session.
        }
    }
}
