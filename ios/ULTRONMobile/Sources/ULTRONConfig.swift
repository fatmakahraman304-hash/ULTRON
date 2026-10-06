import Foundation

enum ULTRONConfig {
    static let baseURL = URL(string: "https://ultron-yubh.onrender.com")!

    static var liveWebSocketURL: URL {
        var parts = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
        parts.scheme = "wss"
        parts.path = "/api/live"
        return parts.url!
    }
}
