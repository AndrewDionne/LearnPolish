import SwiftUI

/// V2 C14/C15/C16: original whole-turn audio and exact meaning are taught
/// before reading/listening assessment. Revealing, skipping or replaying these
/// turns does not record comprehension, review events or personal XP.
struct SourceFirstIntroductionView: View {
    let introduction: NativeSourceIntroLesson
    let onComplete: () -> Void

    @StateObject private var audio = NativeAudio()
    @State private var index = 0
    @State private var playbackRate: Float = 1

    private var item: SourceIntroLine { introduction.items[index] }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 5) {
                Text("Learn the conversation first").font(.title3.bold())
                Text("Hear the original Polish, then read its meaning.")
                    .font(.subheadline).foregroundStyle(.secondary)
            }
            HStack {
                Text("\(index + 1) / \(introduction.items.count)")
                    .monospacedDigit().foregroundStyle(.secondary)
                Spacer()
                Text(introduction.mode == .read ? "Reading" : "Listening")
                    .foregroundStyle(.secondary)
            }
            .font(.footnote)
            ProgressView(value: Double(index + 1),
                         total: Double(introduction.items.count))

            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text(item.polish)
                        .font(.title2.weight(.semibold))
                        .textSelection(.enabled)
                    Text(item.english)
                        .font(.body)
                        .textSelection(.enabled)
                    if let cue = item.teachingCue {
                        Text(cue)
                            .font(.body)
                            .foregroundStyle(.secondary)
                    }
                    HStack {
                        Button {
                            audio.playFile(item.audio, rate: playbackRate)
                        } label: {
                            Label("Hear this line", systemImage: "play.circle.fill")
                        }
                        .buttonStyle(.borderedProminent)
                        Picker("Speed", selection: $playbackRate) {
                            Text("0.75×").tag(Float(0.75))
                            Text("1×").tag(Float(1))
                        }
                        .pickerStyle(.segmented)
                        .frame(maxWidth: 150)
                    }
                    if let message = audio.message {
                        Label(message, systemImage: "info.circle")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 16)
            }
            HStack {
                Button {
                    if index > 0 { index -= 1 }
                } label: {
                    Label("Previous", systemImage: "chevron.left")
                }
                .disabled(index == 0)
                Spacer()
                Button {
                    if index + 1 < introduction.items.count {
                        index += 1
                    } else {
                        audio.discard()
                        onComplete()
                    }
                } label: {
                    Label(index + 1 == introduction.items.count
                          ? (introduction.mode == .read ? "Start reading" : "Start listening")
                          : "Next line",
                          systemImage: "chevron.right")
                }
                .buttonStyle(.borderedProminent)
            }
            Button(introduction.mode == .read
                   ? "Read conversation now"
                   : "Listen without introduction") {
                audio.discard()
                onComplete()
            }
            .font(.footnote)
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.bottom, 10)
        }
        .onDisappear { audio.discard() }
    }
}
