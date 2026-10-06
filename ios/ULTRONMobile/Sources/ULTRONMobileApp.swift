import SwiftUI

@main
struct ULTRONMobileApp: App {
    @StateObject private var voice = BackgroundVoiceController.shared
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(voice)
                .onAppear {
                    voice.configureAudioSession()
                    PhoneActionRouter.shared.requestNotificationPermission()
                }
                .onChange(of: scenePhase) { _, newPhase in
                    voice.handleScenePhase(newPhase)
                }
                .onOpenURL { url in
                    handleDeepLink(url)
                }
        }
    }

    private func handleDeepLink(_ url: URL) {
        guard url.scheme?.lowercased() == "ultron" else { return }

        let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let params = Dictionary(
            uniqueKeysWithValues: (components?.queryItems ?? []).map { ($0.name, $0.value ?? "") }
        )

        switch url.host?.lowercased() {
        case "start":
            Task { await voice.start() }

        case "stop":
            Task { await voice.stop() }

        case "app":
            let name = params["name"] ?? ""
            PhoneActionRouter.shared.handle(action: "open_app", query: name)

        case "youtube":
            PhoneActionRouter.shared.handle(action: "youtube_search", query: params["q"] ?? "")

        case "spotify":
            PhoneActionRouter.shared.handle(action: "spotify_search", query: params["q"] ?? "")

        case "whatsapp":
            PhoneActionRouter.shared.handle(action: "whatsapp_message", query: params["text"] ?? "")

        default:
            break
        }
    }
}
