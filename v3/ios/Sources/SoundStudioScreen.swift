import SwiftUI

/// The alphabet plays original COMPLETE recorded words as examples.
/// It never represents these as isolated letter/phoneme recordings.
struct SoundStudioScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @State private var section = 0

    var body: some View {
        Group {
            if let sound = learner.soundStudio {
                VStack(spacing: 12) {
                    Picker("Sound study", selection: $section) {
                        Text("Alphabet").tag(0)
                        Text("Sound lab").tag(1)
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    if section == 0 {
                        AlphabetExamplesScreen(sound: sound)
                    } else {
                        List(sound.soundLessons) { lesson in
                            NavigationLink {
                                SoundContrastScreen(lesson: lesson)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(lesson.title).font(.headline)
                                    Text("\(lesson.groups.count) sounds · \(lesson.questions.count) recordings")
                                        .foregroundStyle(.secondary).font(.caption)
                                }
                                .padding(.vertical, 6)
                            }
                        }
                    }
                }
            } else {
                ContentUnavailableView("Sound lessons unavailable", systemImage: "waveform",
                    description: Text(learner.catalogError ?? "Source recordings have not been prepared."))
            }
        }
        .navigationTitle("Sounds")
    }
}

private struct AlphabetExamplesScreen: View {
    let sound: NativeSoundStudio
    var body: some View {
        List {
            Text("Hear the highlighted letter in a complete Polish word. These are original word recordings, not individual letter names.")
                .font(.footnote).foregroundStyle(.secondary)
            Section("Polish alphabet") {
                ForEach(sound.letters) { item in
                    AlphabetExampleRow(item: item)
                }
            }
            Section("Common combinations") {
                ForEach(sound.combinations) { item in
                    AlphabetExampleRow(item: item)
                }
            }
        }
    }
}

private struct AlphabetExampleRow: View {
    let item: NativeSoundRecord
    @StateObject private var audio = NativeAudio()
    @State private var speed: Float = 1

    var body: some View {
        HStack(spacing: 12) {
            Text(item.label ?? "")
                .font(.title2.bold())
                .foregroundStyle(.indigo)
                .frame(width: 64, alignment: .leading)
            VStack(alignment: .leading, spacing: 4) {
                SoundFocusedText(polish: item.polish, focus: item.focus)
                    .font(.headline)
                Text(item.english).font(.caption).foregroundStyle(.secondary)
            }
            Spacer(minLength: 8)
            Button {
                audio.playFile(item.audio, rate: 1)
            } label: {
                Image(systemName: "play.circle.fill").font(.title2)
            }
            .buttonStyle(.borderless)
            .accessibilityLabel("Hear \(item.polish)")
        }
        .padding(.vertical, 6)
    }
}

struct SoundFocusedText: View {
    let polish: String
    let focus: String

    var body: some View {
        Group {
            if !focus.isEmpty, let range = polish.range(of: focus),
               polish.range(of: focus, range: range.upperBound..<polish.endIndex) == nil {
                Text(String(polish[..<range.lowerBound]))
                + Text(focus).bold().foregroundColor(.indigo)
                + Text(String(polish[range.upperBound...]))
            } else {
                Text(polish)
            }
        }
    }
}

struct SoundContrastScreen: View {
    let lesson: NativeSoundLesson
    @StateObject private var audio = NativeAudio()
    @State private var quiz = false
    @State private var position = 0
    @State private var choice: String?

    private var card: NativeSoundRecord { lesson.questions[position] }
    private var answer: SoundGroup? {
        guard let id = card.groupId else { return nil }
        return lesson.groups.first(where: { $0.id == id })
    }

    var body: some View {
        VStack(spacing: 12) {
            Picker("Exercise", selection: $quiz) {
                Text("Compare words").tag(false)
                Text("Test my ear").tag(true)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            if quiz {
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        Text("\(position + 1) / \(lesson.questions.count)")
                            .font(.subheadline.monospacedDigit())
                            .foregroundStyle(.secondary)
                        ProgressView(value: Double(position + 1), total: Double(lesson.questions.count))
                        Text("Listen to the word. Which sound is highlighted?")
                            .font(.headline)
                        Button {
                            audio.playFile(card.audio, rate: 1)
                        } label: {
                            Label("Hear word", systemImage: "play.circle.fill")
                        }
                        .buttonStyle(.borderedProminent)
                        ForEach(lesson.groups) { group in
                            Button(group.label) { choice = group.id }
                                .buttonStyle(.bordered)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .disabled(choice != nil)
                        }
                        if choice != nil {
                            Text(choice == card.groupId ? "Correct." : "This word demonstrates:")
                                .font(.headline)
                            Text(answer?.label ?? "").font(.title2)
                            SoundFocusedText(polish: card.polish, focus: card.focus)
                                .font(.title)
                            Text(card.english).foregroundStyle(.secondary)
                            Button(position + 1 == lesson.questions.count ? "Practice again" : "Next word") {
                                position = position + 1 == lesson.questions.count ? 0 : position + 1
                                choice = nil
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        Text("This ear exercise is for listening practice. It does not claim to grade your pronunciation.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
                }
            } else {
                List {
                    if !lesson.intro.isEmpty {
                        Text(lesson.intro).foregroundStyle(.secondary)
                    }
                    ForEach(lesson.groups) { group in
                        Section {
                            Text(group.hint).font(.footnote).foregroundStyle(.secondary)
                            ForEach(lesson.questions.filter { $0.groupId == group.id }) { item in
                                HStack(spacing: 12) {
                                    VStack(alignment: .leading, spacing: 4) {
                                        SoundFocusedText(polish: item.polish, focus: item.focus)
                                            .font(.headline)
                                        Text(item.english).font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Button {
                                        audio.playFile(item.audio, rate: 1)
                                    } label: {
                                        Image(systemName: "play.circle.fill")
                                    }
                                    .buttonStyle(.borderless)
                                    .accessibilityLabel("Hear \(item.polish)")
                                }
                                .padding(.vertical, 3)
                            }
                        } header: {
                            Text(group.label)
                        }
                    }
                }
            }
            if let message = audio.message {
                Text(message).foregroundStyle(.secondary).font(.footnote).padding(.horizontal)
            }
        }
        .navigationTitle(lesson.title)
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: quiz) { _, _ in position = 0; choice = nil }
        .onDisappear { audio.discard() }
    }
}
