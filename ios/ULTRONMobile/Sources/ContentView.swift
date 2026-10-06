import SwiftUI

struct ContentView: View {
    @EnvironmentObject var voice: BackgroundVoiceController
    @State private var password = ""

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 18) {
                Text("ULTRON")
                    .font(.system(size: 34, weight: .black, design: .rounded))
                    .foregroundStyle(.red)

                Text(voice.status)
                    .foregroundStyle(.white.opacity(0.8))
                    .multilineTextAlignment(.center)

                if !voice.lastTranscript.isEmpty {
                    Text(voice.lastTranscript)
                        .foregroundStyle(.white)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(.white.opacity(0.06))
                        .clipShape(RoundedRectangle(cornerRadius: 18))
                }

                if voice.needsLogin {
                    SecureField("ULTRON Cloud parolası", text: $password)
                        .textContentType(.password)
                        .padding()
                        .background(.white.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                        .foregroundStyle(.white)

                    Button("Cloud'a bağlan") {
                        Task { await voice.login(password: password) }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                }

                Button(voice.listening ? "SÜREKLİ DİNLEMEYİ DURDUR" : "SÜREKLİ DİNLEMEYİ BAŞLAT") {
                    Task {
                        if voice.listening { await voice.stop() }
                        else { await voice.start() }
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(voice.listening ? .gray : .red)

                Text("Arka plan ses oturumu native iOS uygulamasında devam edebilir. iOS güvenliği nedeniyle ULTRON başka bir uygulamanın ekranındaki butonlara basamaz veya YouTube reklamını otomatik atlayamaz.")
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.5))
                    .multilineTextAlignment(.center)
            }
            .padding(24)
        }
        .preferredColorScheme(.dark)
    }
}
