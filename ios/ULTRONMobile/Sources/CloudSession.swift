import Foundation

actor CloudSession {
    static let shared = CloudSession()

    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.httpCookieStorage = .shared
        config.httpShouldSetCookies = true
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
        let (_, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode == 200 { return }
        guard let password = KeychainStore.read(account: "cloud-password") else {
            throw URLError(.userAuthenticationRequired)
        }
        try await login(password: password)
    }

    func webSocketTask() -> URLSessionWebSocketTask {
        session.webSocketTask(with: ULTRONConfig.liveWebSocketURL)
    }
}
