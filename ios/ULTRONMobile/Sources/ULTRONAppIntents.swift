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

/// Foreground app/microphone not required: Siri sends one authenticated HTTP
/// command to Cloud, with the desktop retaining its own permission gate.
struct SendULTRONDesktopTaskIntent: AppIntent {
    static var title: LocalizedStringResource = "ULTRON Bilgisayara Görev Gönder"
    static var description = IntentDescription("Siri veya Kestirmeler ile masaüstü ULTRON'a görev kuyruğa alır; riskli işlemler onaya tabidir.")
    // iOS 18-compatible: App Intent defaults to running without opening the app.
    static var openAppWhenRun = false

    @Parameter(title: "Bilgisayara gönderilecek görev")
    var task: String

    static var parameterSummary: some ParameterSummary {
        Summary("Bilgisayara \(\.$task) gönder")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let id = try await CloudSession.shared.enqueueDesktopTask(task)
        return .result(dialog: IntentDialog("Görev \(id) bilgisayardaki ULTRON kuyruğuna alındı. Henüz tamamlanmadı."))
    }
}

/// General Siri question to the shared ULTRON cloud brain. Does not
/// control local apps or tools and does not require a live mic session.
struct AskULTRONIntent: AppIntent {
    static var title: LocalizedStringResource = "ULTRON'a Sor"
    static var description = IntentDescription("Siri ile ULTRON'a soru sor, ortak Cloud hafızasından cevap al.")
    static var openAppWhenRun = false

    @Parameter(title: "ULTRON'a sorulacak soru")
    var question: String

    static var parameterSummary: some ParameterSummary {
        Summary("ULTRON'a \(\.$question) sor")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let reply = try await CloudSession.shared.askULTRON(question)
        return .result(dialog: IntentDialog("\(String(reply.prefix(900)))"))
    }
}

struct ULTRONAppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AskULTRONIntent(),
            phrases: [
                "\(.applicationName) soru sor",
                "\(.applicationName) bana cevap ver"
            ],
            shortTitle: "ULTRON'a Sor",
            systemImageName: "brain"
        )

        AppShortcut(
            intent: SendULTRONDesktopTaskIntent(),
            phrases: [
                "\(.applicationName) bilgisayara görev gönder",
                "\(.applicationName) ile bilgisayara komut gönder"
            ],
            shortTitle: "Bilgisayara Gönder",
            systemImageName: "laptopcomputer"
        )

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
