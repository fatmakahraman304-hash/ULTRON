import SwiftUI

struct ContentView: View {
    @EnvironmentObject var voice: BackgroundVoiceController
    @StateObject private var router = PhoneActionRouter.shared
    @State private var password = ""
    @State private var desktopTask = ""
    @State private var sendingTask = false
    @State private var desktopTaskStatus = ""

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.black, Color(red: 0.08, green: 0.0, blue: 0.01)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 18) {
                    header
                    connectionCard
                    transcriptCard

                    if voice.needsLogin {
                        loginCard
                    }

                    if !router.pendingActionText.isEmpty {
                        pendingActionCard
                    }

                    controlCard
                    desktopTaskCard
                    limitsCard
                }
                .padding(20)
            }
        }
        .preferredColorScheme(.dark)
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("ULTRON")
                    .font(.system(size: 34, weight: .black, design: .rounded))
                    .foregroundStyle(.red)

                Text("NATIVE iPHONE")
                    .font(.caption.weight(.bold))
                    .tracking(2)
                    .foregroundStyle(.white.opacity(0.45))
            }

            Spacer()

            Circle()
                .fill(voice.connected ? Color.green : (voice.desiredListening ? Color.orange : Color.gray))
                .frame(width: 12, height: 12)
                .shadow(color: voice.connected ? .green.opacity(0.8) : .clear, radius: 8)
        }
    }

    private var connectionCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label(
                    voice.connected ? "CLOUD LIVE BAĞLI" : (voice.desiredListening ? "YENİDEN BAĞLANIYOR" : "SES KAPALI"),
                    systemImage: voice.connected ? "waveform.circle.fill" : "waveform.circle"
                )
                .font(.caption.weight(.black))
                .foregroundStyle(voice.connected ? .green : .white.opacity(0.75))

                Spacer()

                if voice.isBackground {
                    Text("ARKA PLAN")
                        .font(.caption2.weight(.black))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .background(.red.opacity(0.16))
                        .clipShape(Capsule())
                }
            }

            Text(voice.status)
                .foregroundStyle(.white)
                .font(.body.weight(.medium))

            if voice.reconnectAttempt > 0 && !voice.connected {
                Text("Yeniden bağlanma denemesi: \(voice.reconnectAttempt)")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.45))
            }
        }
        .ultronCard()
    }

    @ViewBuilder
    private var transcriptCard: some View {
        if !voice.lastTranscript.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("SON DUYULAN")
                    .font(.caption2.weight(.black))
                    .tracking(1.2)
                    .foregroundStyle(.red)

                Text(voice.lastTranscript)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .ultronCard()
        }
    }

    private var loginCard: some View {
        VStack(spacing: 12) {
            SecureField("ULTRON Cloud parolası", text: $password)
                .textContentType(.password)
                .padding()
                .background(.white.opacity(0.06))
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .foregroundStyle(.white)

            Button("CLOUD'A BAĞLAN") {
                Task {
                    await voice.login(password: password)
                    password = ""
                }
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
            .frame(maxWidth: .infinity)
        }
        .ultronCard()
    }

    private var pendingActionCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("BEKLEYEN TELEFON KOMUTU")
                .font(.caption2.weight(.black))
                .tracking(1.2)
                .foregroundStyle(.orange)

            Text(router.pendingActionText)
                .foregroundStyle(.white)

            HStack {
                Button("DEVAM ET") {
                    router.resumePendingActionIfPossible(userInitiated: true)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)

                Button("SİL") {
                    router.clearPending()
                }
                .buttonStyle(.bordered)
            }
        }
        .ultronCard()
    }

    private var controlCard: some View {
        VStack(spacing: 12) {
            Button {
                Task {
                    if voice.desiredListening {
                        await voice.stop()
                    } else {
                        await voice.start()
                    }
                }
            } label: {
                HStack {
                    Image(systemName: voice.desiredListening ? "stop.circle.fill" : "mic.circle.fill")
                    Text(voice.desiredListening ? "SÜREKLİ DİNLEMEYİ DURDUR" : "SÜREKLİ DİNLEMEYİ BAŞLAT")
                        .fontWeight(.black)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
            }
            .buttonStyle(.borderedProminent)
            .tint(voice.desiredListening ? .gray : .red)

            Text("Dinleme açıkken ULTRON, uygulama arka plandayken ses oturumunu korumaya ve Cloud bağlantısı koparsa otomatik yeniden bağlanmaya çalışır.")
                .font(.footnote)
                .foregroundStyle(.white.opacity(0.5))
                .multilineTextAlignment(.center)
        }
        .ultronCard()
    }

    private var desktopTaskCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("BİLGİSAYARDAKİ ULTRON", systemImage: "laptopcomputer")
                .font(.caption.weight(.black))
                .foregroundStyle(.red)

            Text("Siri'den 'ULTRON bilgisayara görev gönder' diyebilir veya yazabilirsin. Laptop çevrimdışıysa Cloud kuyruğunda bekler.")
                .font(.footnote)
                .foregroundStyle(.white.opacity(0.65))

            TextField("Laptopta yapılacak görevi yaz", text: $desktopTask, axis: .vertical)
                .lineLimit(2...4)
                .padding(12)
                .background(.white.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 10))

            Button {
                let message = desktopTask
                sendingTask = true
                Task {
                    do {
                        let id = try await CloudSession.shared.enqueueDesktopTask(message)
                        desktopTaskStatus = "Görev #\(id) Cloud kuyruğuna alındı. Henüz tamamlanmadı."
                        desktopTask = ""
                    } catch {
                        desktopTaskStatus = "Görev gönderilemedi: \(error.localizedDescription)"
                    }
                    sendingTask = false
                }
            } label: {
                Label(sendingTask ? "GÖNDERİLİYOR…" : "BİLGİSAYARA GÖNDER", systemImage: "paperplane.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
            .disabled(sendingTask || desktopTask.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

            Button("SON GÖREVİN DURUMUNU ÖĞREN") {
                Task {
                    do {
                        desktopTaskStatus = try await CloudSession.shared.latestDesktopTaskStatus()
                    } catch {
                        desktopTaskStatus = "Durum alınamadı: \(error.localizedDescription)"
                    }
                }
            }
            .buttonStyle(.bordered)
            .tint(.red)

            if !desktopTaskStatus.isEmpty {
                Text(desktopTaskStatus)
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.8))
            }
        }
        .ultronCard()
    }

    private var limitsCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("iOS SINIRI")
                .font(.caption2.weight(.black))
                .tracking(1.2)
                .foregroundStyle(.white.opacity(0.45))

            Text("ULTRON arka planda seni dinleyip konuşabilir ve komut hazırlayabilir. Ancak iOS, başka bir uygulamanın ekranındaki düğmelere gizlice basmaya izin vermez. Örneğin YouTube reklamındaki “Atla” düğmesine otomatik dokunamaz veya WhatsApp'ta kullanıcı onayı olmadan Gönder'e basamaz.")
                .font(.footnote)
                .foregroundStyle(.white.opacity(0.5))
        }
        .ultronCard()
    }
}

private extension View {
    func ultronCard() -> some View {
        self
            .padding(16)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 20)
                    .fill(Color.white.opacity(0.045))
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(Color.red.opacity(0.32), lineWidth: 1)
                    )
            )
    }
}
