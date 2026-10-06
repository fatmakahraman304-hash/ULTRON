import SwiftUI

@main
struct ULTRONMobileApp: App {
    @StateObject private var voice = BackgroundVoiceController()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(voice)
                .onAppear {
                    voice.configureAudioSession()
                }
        }
    }
}
