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
        }
    }
}
