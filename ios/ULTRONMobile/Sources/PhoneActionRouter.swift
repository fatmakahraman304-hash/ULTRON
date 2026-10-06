import Foundation
import UIKit
import UserNotifications

struct PendingPhoneAction: Codable, Equatable {
    let action: String
    let query: String
    let createdAt: Date
}

@MainActor
final class PhoneActionRouter: ObservableObject {
    static let shared = PhoneActionRouter()

    @Published var pendingActionText = ""

    private let defaultsKey = "ultron.pendingPhoneAction"

    private init() {
        refreshPendingLabel()
    }

    func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
    }

    func handle(action: String, query: String) {
        let item = PendingPhoneAction(action: action, query: query, createdAt: Date())

        guard UIApplication.shared.applicationState == .active else {
            savePending(item)
            notifyPending(item)
            return
        }

        open(item)
    }

    func resumePendingActionIfPossible() {
        guard UIApplication.shared.applicationState == .active,
              let item = loadPending() else { return }

        clearPending()
        open(item)
    }

    func clearPending() {
        UserDefaults.standard.removeObject(forKey: defaultsKey)
        pendingActionText = ""
    }

    private func savePending(_ item: PendingPhoneAction) {
        guard let data = try? JSONEncoder().encode(item) else { return }
        UserDefaults.standard.set(data, forKey: defaultsKey)
        refreshPendingLabel()
    }

    private func loadPending() -> PendingPhoneAction? {
        guard let data = UserDefaults.standard.data(forKey: defaultsKey) else { return nil }
        return try? JSONDecoder().decode(PendingPhoneAction.self, from: data)
    }

    private func refreshPendingLabel() {
        guard let item = loadPending() else {
            pendingActionText = ""
            return
        }

        let base: String
        switch item.action {
        case "open_app":
            base = "\(item.query.capitalized) açılmaya hazır"
        case "youtube_search":
            base = "YouTube araması hazır: \(item.query)"
        case "spotify_search":
            base = "Spotify araması hazır: \(item.query)"
        case "whatsapp_message":
            base = "WhatsApp mesajı hazır"
        case "maps":
            base = "Harita komutu hazır"
        default:
            base = "Telefon komutu hazır"
        }
        pendingActionText = base
    }

    private func notifyPending(_ item: PendingPhoneAction) {
        let content = UNMutableNotificationContent()
        content.title = "ULTRON"
        content.body = pendingDescription(item)
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: "ultron.pending.\(UUID().uuidString)",
            content: content,
            trigger: nil
        )
        UNUserNotificationCenter.current().add(request, withCompletionHandler: nil)
    }

    private func pendingDescription(_ item: PendingPhoneAction) -> String {
        switch item.action {
        case "open_app":
            return "\(item.query.capitalized) açma komutu hazır. ULTRON'a dönünce devam edecek."
        case "youtube_search":
            return "YouTube'da “\(item.query)” araması hazır."
        case "spotify_search":
            return "Spotify'da “\(item.query)” araması hazır."
        case "whatsapp_message":
            return "WhatsApp mesajı hazırlandı."
        default:
            return "Telefon komutu hazır. ULTRON'a dönünce devam edecek."
        }
    }

    private func open(_ item: PendingPhoneAction) {
        guard let url = buildURL(action: item.action, query: item.query) else { return }

        UIApplication.shared.open(url, options: [:]) { [weak self] success in
            Task { @MainActor in
                if !success {
                    self?.pendingActionText = "iOS bu işlemi doğrudan açmadı."
                }
            }
        }
    }

    private func buildURL(action: String, query: String) -> URL? {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let encodedQuery = trimmed.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""

        let raw: String?
        switch action {
        case "open_app":
            raw = [
                "youtube": "youtube://",
                "spotify": "spotify://",
                "whatsapp": "whatsapp://",
                "instagram": "instagram://",
                "chrome": "googlechrome://",
                "maps": "maps://"
            ][trimmed.lowercased()]

        case "youtube_search":
            raw = "https://www.youtube.com/results?search_query=\(encodedQuery)"

        case "spotify_search":
            raw = "https://open.spotify.com/search/\(encodedQuery)"

        case "whatsapp_message":
            raw = "whatsapp://send?text=\(encodedQuery)"

        case "maps":
            raw = trimmed.isEmpty
                ? "https://maps.apple.com/"
                : "https://maps.apple.com/?q=\(encodedQuery)"

        case "search_web":
            raw = "https://www.google.com/search?q=\(encodedQuery)"

        case "browser":
            raw = "googlechrome://"

        case "sms":
            raw = trimmed.isEmpty ? "sms:" : "sms:\(trimmed)"

        case "email":
            raw = trimmed.isEmpty ? "mailto:" : "mailto:\(encodedQuery)"

        case "call":
            raw = "tel:\(trimmed.filter { $0.isNumber || $0 == "+" })"

        case "facetime":
            raw = "facetime:\(encodedQuery)"

        default:
            raw = nil
        }

        guard let raw else { return nil }
        return URL(string: raw)
    }
}
