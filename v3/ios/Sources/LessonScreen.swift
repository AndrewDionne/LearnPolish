import SwiftUI

struct LessonScreen: View {
    let lesson: Lesson
    var startItemID: String? = nil
    var preferredMode: PracticeMode? = nil

    @EnvironmentObject private var learner: LocalLearningStore
    @StateObject private var audio = NativeAudio()
    @State private var index = 0
    @State private var mode: PracticeMode = .learn
    @State private var revealed = false
    @State private var selectedOption: String?
    @State private var playbackRate: Float = 1
    @State private var guideVisible = false
    @State private var finished = false

    private var item: LessonItem { lesson.items[index] }

    var body: some View {
        VStack(spacing: 12) {
            if !finished {
                HStack {
                    Text("\(index + 1) / \(lesson.items.count)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(lesson.title)
                        .font(.subheadline)
                        .lineLimit(1)
                }
                ProgressView(value: Double(index + 1), total: Double(lesson.items.count))

                Picker("Practice", selection: $mode) {
                    ForEach(lesson.availableModes) { option in
                        Text(option.label).tag(option)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.vertical, 6)

                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        switch mode {
                        case .learn: learnCard
                        case .listen: listenCard
                        case .read: readCard
                        case .speak: speakCard
                        }
                        if let message = audio.message {
                            Label(message, systemImage: "info.circle")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        if let error = learner.saveError {
                            Label(error, systemImage: "exclamationmark.triangle")
                                .font(.footnote)
                                .foregroundStyle(.red)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 28)
                }

                HStack {
                    Button {
                        if index > 0 { index -= 1; finished = false }
                    } label: {
                        Label("Previous", systemImage: "chevron.left")
                    }
                    .disabled(index == 0)
                    Spacer()
                    Button {
                        advance()
                    } label: {
                        Label(index + 1 == lesson.items.count ? "Finish" : "Next",
                              systemImage: "chevron.right")
                    }
                    .buttonStyle(.borderedProminent)
                }
                .padding(.bottom, 8)
            } else {
                Spacer()
                ContentUnavailableView("Session finished", systemImage: "checkmark.circle",
                                       description: Text("Your progress is saved on this iPhone."))
                Button("Practise again") { index = 0; finished = false; resetCard() }
                    .buttonStyle(.borderedProminent)
                Spacer()
            }
        }
        .padding(.horizontal)
        .navigationTitle(lesson.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if let preferredMode, lesson.availableModes.contains(preferredMode) {
                mode = preferredMode
            } else if learner.profile.lastLessonID == lesson.id,
                      let recentMode = learner.profile.lastMode,
                      lesson.availableModes.contains(recentMode) {
                mode = recentMode
            } else {
                mode = lesson.availableModes.first ?? .learn
            }
            let resumeID = startItemID ?? (learner.profile.lastLessonID == lesson.id
                                           ? learner.profile.lastItemID : nil)
            if let resumeID, let position = lesson.items.firstIndex(where: { $0.id == resumeID }) {
                index = position
            }
            remember()
        }
        .onDisappear { audio.discard() }
        .onChange(of: index) { _, _ in resetCard(); remember() }
        .onChange(of: mode) { _, _ in resetCard(); remember() }
    }

    private var learnCard: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(item.polish)
                .font(.largeTitle.weight(.semibold))
                .textSelection(.enabled)
            if let path = item.audio, !path.isEmpty {
                referenceControls
            }
            if revealed {
                Text(item.english)
                    .font(.title3)
                HStack(spacing: 12) {
                    Button("Needs practice") { rate(false) }
                        .buttonStyle(.bordered)
                    Button("Got it") { rate(true) }
                        .buttonStyle(.borderedProminent)
                }
            } else {
                Button("Show meaning") { revealed = true }
                    .buttonStyle(.borderedProminent)
            }
        }
    }

    private var listenCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label("Listen", systemImage: "headphones").font(.headline)
            Text("Listen to the Polish recording and choose its meaning.")
                .foregroundStyle(.secondary)
            referenceControls
            let choices = listenChoices
            if choices.count >= 3 {
                ForEach(choices, id: \.self) { choice in
                    Button {
                        guard selectedOption == nil else { return }
                        selectedOption = choice
                        learner.recordAttempt(item: item, mode: .listen,
                                              understood: choice == item.english)
                    } label: {
                        HStack {
                            Text(choice)
                                .multilineTextAlignment(.leading)
                            Spacer()
                            if selectedOption == choice {
                                Image(systemName: choice == item.english ? "checkmark.circle" : "xmark.circle")
                            }
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.bordered)
                    .disabled(selectedOption != nil)
                }
                if selectedOption != nil {
                    Text(item.polish).font(.title2.bold())
                    Text("Meaning: " + item.english)
                }
            } else {
                Text("Choose when to reveal the written meaning.")
                if revealed {
                    Text(item.polish).font(.title2)
                    Text(item.english)
                    ratingControls(for: .listen)
                } else {
                    Button("Reveal meaning") { revealed = true }
                        .buttonStyle(.bordered)
                }
            }
        }
    }

    private var readCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label("Read", systemImage: "book").font(.headline)
            Text(item.polish)
                .font(.title2)
                .textSelection(.enabled)
            if item.audio != nil { referenceControls }
            if let check = item.comprehension, check.options.indices.contains(check.correctIndex) {
                Text(check.prompt).font(.headline)
                ForEach(check.options, id: \.self) { option in
                    Button(option) {
                        guard selectedOption == nil else { return }
                        selectedOption = option
                        learner.recordAttempt(item: item, mode: .read,
                                              understood: option == check.options[check.correctIndex])
                    }
                    .buttonStyle(.bordered)
                    .disabled(selectedOption != nil)
                }
                if selectedOption != nil {
                    Text(item.english)
                    Text(check.feedback).foregroundStyle(.secondary)
                }
            } else if revealed {
                Text(item.english).font(.title3)
                ratingControls(for: .read)
            } else {
                Button("Show translation") { revealed = true }
                    .buttonStyle(.borderedProminent)
            }
        }
    }

    private var speakCard: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(item.polish)
                .font(.largeTitle.weight(.semibold))
                .textSelection(.enabled)
            if item.audio != nil { referenceControls }
            if let pronunciation = item.pronunciation, !pronunciation.isEmpty {
                Toggle("Pronunciation guide", isOn: $guideVisible)
                if guideVisible {
                    Text(pronunciation).font(.title3).foregroundStyle(.secondary)
                }
            }
            HStack(spacing: 12) {
                if audio.isRecording {
                    Button {
                        audio.stopRecording()
                    } label: {
                        Label("Stop", systemImage: "stop.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                } else {
                    Button {
                        audio.requestRecord()
                    } label: {
                        Label(audio.hasRecording ? "Record again" : "Record", systemImage: "mic")
                    }
                    .buttonStyle(.borderedProminent)
                }
                if audio.hasRecording && !audio.isRecording {
                    Button {
                        audio.playRecording()
                    } label: {
                        Label("Replay", systemImage: "play.fill")
                    }
                    .buttonStyle(.bordered)
                }
            }
            if audio.isRecording {
                Text("Recording… up to 10 seconds")
                    .foregroundStyle(.secondary)
            }
            if audio.hasRecording && !audio.isRecording {
                Text("Your take stays on this device. Automatic pronunciation scoring is not enabled.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                Button("Mark practised") {
                    learner.recordAttempt(item: item, mode: .speak, understood: nil)
                    advance()
                }
                .buttonStyle(.bordered)
            }
        }
    }

    private var referenceControls: some View {
        HStack(spacing: 12) {
            Button {
                audio.playReference(item, rate: playbackRate)
            } label: {
                Label("Play Polish", systemImage: "play.circle.fill")
            }
            .buttonStyle(.bordered)
            Picker("Speed", selection: $playbackRate) {
                Text("0.75×").tag(Float(0.75))
                Text("1×").tag(Float(1))
            }
            .pickerStyle(.segmented)
            .frame(maxWidth: 150)
        }
    }

    private var listenChoices: [String] {
        var choices = [item.english]
        for candidate in lesson.items where candidate.id != item.id {
            if !choices.contains(candidate.english) { choices.append(candidate.english) }
            if choices.count == 3 { break }
        }
        return choices.sorted()
    }

    private func ratingControls(for mode: PracticeMode) -> some View {
        HStack(spacing: 12) {
            Button("Needs practice") {
                learner.recordAttempt(item: item, mode: mode, understood: false)
                advance()
            }
            .buttonStyle(.bordered)
            Button("Understood") {
                learner.recordAttempt(item: item, mode: mode, understood: true)
                advance()
            }
            .buttonStyle(.borderedProminent)
        }
    }

    private func rate(_ success: Bool) {
        learner.recordAttempt(item: item, mode: .learn, understood: success)
        advance()
    }

    private func advance() {
        if index < lesson.items.count - 1 {
            index += 1
        } else {
            audio.discard()
            finished = true
        }
    }

    private func remember() {
        guard !finished else { return }
        learner.rememberPosition(lesson: lesson, item: item, mode: mode)
    }

    private func resetCard() {
        revealed = false
        selectedOption = nil
        guideVisible = false
        audio.discard()
    }
}
