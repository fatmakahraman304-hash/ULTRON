import Foundation

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
