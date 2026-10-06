import AppIntents

struct StartULTRONListeningIntent: AppIntent {
    static var title: LocalizedStringResource = "ULTRON Dinlemeyi Başlat"
    static var description = IntentDescription("ULTRON'un sürekli sesli dinleme oturumunu başlatır.")
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        await BackgroundVoiceController.shared.start()
        return .result(dialog: "ULTRON dinlemeye başlıyor.")
    }
}

struct StopULTRONListeningIntent: AppIntent {
    static var title: LocalizedStringResource = "ULTRON Dinlemeyi Durdur"
    static var description = IntentDescription("ULTRON'un sürekli sesli dinleme oturumunu durdurur.")
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult & ProvidesDialog {
        await BackgroundVoiceController.shared.stop()
        return .result(dialog: "ULTRON dinlemeyi durdurdu.")
    }
}

struct ULTRONAppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: StartULTRONListeningIntent(),
            phrases: [
                "\(.applicationName) dinlemeye başla",
                "\(.applicationName) sesi aç",
                "\(.applicationName) ile konuş"
            ],
            shortTitle: "ULTRON Dinle",
            systemImageName: "waveform.circle.fill"
        )

        AppShortcut(
            intent: StopULTRONListeningIntent(),
            phrases: [
                "\(.applicationName) dinlemeyi durdur",
                "\(.applicationName) sesi kapat"
            ],
            shortTitle: "ULTRON Durdur",
            systemImageName: "stop.circle.fill"
        )
    }
}
