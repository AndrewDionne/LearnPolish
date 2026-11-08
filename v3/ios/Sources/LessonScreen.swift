import SwiftUI

struct LessonScreen: View {
    let lesson: Lesson
    var startItemID: String? = nil
    var preferredMode: PracticeMode? = nil
    // Frozen review item IDs captured when the learner opens the review session.
    var dueItemIDs: [String]? = nil
    var resumeAtNextUnseen: Bool = false

    @EnvironmentObject private var learner: LocalLearningStore
    @StateObject private var audio = NativeAudio()
    @State private var index = 0
    @State private var batch = 0
    @State private var mode: PracticeMode = .learn
    @State private var revealed = false
    @State private var selectedOption: String?
    @State private var playbackRate: Float = 1
    @State private var guideVisible = false
    @State private var finished = false
    @State private var showingSourceIntroduction = false

    private var sourceIntroduction: NativeSourceIntroLesson? {
        learner.sourceExposure?.preparation(for: lesson, mode: mode)
    }

    private var sections: [PracticeSection] {
        NativePracticeRules.sections(for: lesson, mode: mode)
    }

    private var currentItems: [LessonItem] {
        if let dueItemIDs {
            let selected = Set(dueItemIDs)
            return lesson.items.filter { selected.contains($0.id) }
        }
        return sections[min(batch, max(0, sections.count - 1))].items
    }

    private var item: LessonItem { currentItems[index] }

    var body: some View {
        VStack(spacing: 12) {
            if showingSourceIntroduction, let original = sourceIntroduction, dueItemIDs == nil {
                SourceFirstIntroductionView(introduction: original) {
                    showingSourceIntroduction = false
                }
            } else if !finished {
                HStack {
                    Text("\(index + 1) / \(currentItems.count)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(lesson.title)
                        .font(.subheadline)
                        .lineLimit(1)
                }
                ProgressView(value: Double(index + 1), total: Double(currentItems.count))

                Picker("Practice", selection: $mode) {
                    ForEach(dueItemIDs == nil ? lesson.availableModes : [.learn]) { option in
                        Text(option.label).tag(option)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.vertical, 6)

                if dueItemIDs == nil && sections.count > 1 {
                    Picker("Numbers practice", selection: $batch) {
                        ForEach(sections) { section in
                            Text(section.title).tag(section.id)
                        }
                    }
                    .pickerStyle(.segmented)
                }

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
                        Label(index + 1 == currentItems.count ? "Finish" : "Next",
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
                if dueItemIDs == nil && batch + 1 < sections.count {
                    Button("Next section") {
                        batch += 1
                        index = 0
                        finished = false
                        resetCard()
                        remember()
                    }
                    .buttonStyle(.bordered)
                }
                if let following = learner.coreJourney?.next(after: lesson.id), dueItemIDs == nil {
                    NavigationLink {
                        LessonScreen(lesson: following, resumeAtNextUnseen: true)
                    } label: {
                        Label("Next lesson", systemImage: "arrow.right")
                    }
                    .buttonStyle(.bordered)
                }
                Spacer()
            }
        }
        .padding(.horizontal)
        .navigationTitle(lesson.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if dueItemIDs != nil {
                mode = .learn
            } else if resumeAtNextUnseen {
                mode = lesson.kind == "reading" ? .read : .learn
            } else if let preferredMode, lesson.availableModes.contains(preferredMode) {
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
            if dueItemIDs == nil {
                batch = NativePracticeRules.firstUnvisitedBatch(for: lesson,
                                                               progress: learner.profile.records)
                if let resumeID,
                   let section = sections.firstIndex(where: { section in
                       section.items.contains(where: { $0.id == resumeID })
                   }) {
                    batch = section
                }
            }
            let available = currentItems
            if !resumeAtNextUnseen, let resumeID,
               let position = available.firstIndex(where: { $0.id == resumeID }) {
                index = position
            } else {
                index = NativePracticeRules.nextUnseenIndex(items: available,
                                                            progress: learner.profile.records,
                                                            mode: mode)
            }
            showingSourceIntroduction = dueItemIDs == nil && sourceIntroduction != nil
            remember()
        }
        .onDisappear { audio.discard() }
        .onChange(of: index) { _, _ in resetCard(); remember() }
        .onChange(of: mode) { _, _ in
            showingSourceIntroduction = dueItemIDs == nil && sourceIntroduction != nil
            batch = 0
            index = 0
            finished = false
            resetCard()
            remember()
        }
        .onChange(of: batch) { _, _ in
            index = 0
            finished = false
            resetCard()
            remember()
        }
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
            if choices.count >= 2 {
                ForEach(choices, id: \.self) { choice in
                    Button {
                        guard selectedOption == nil else { return }
                        selectedOption = choice
                        learner.recordAttempt(item: item, mode: .listen,
                                              understood: choice == (item.comprehension.flatMap {
                                                  $0.options.indices.contains($0.correctIndex)
                                                    ? $0.options[$0.correctIndex] : nil
                                              } ?? item.english))
                    } label: {
                        HStack {
                            Text(choice)
                                .multilineTextAlignment(.leading)
                            Spacer()
                            if selectedOption == choice {
                                Image(systemName: choice == (item.comprehension.flatMap {
                                    $0.options.indices.contains($0.correctIndex)
                                        ? $0.options[$0.correctIndex] : nil
                                } ?? item.english) ? "checkmark.circle" : "xmark.circle")
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
                NativeSpeechPracticePanel(item: item, audio: audio)
                    .id(item.id)
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
        NativePracticeRules.choices(for: lesson, item: item, itemIndex: index)
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
        if index < currentItems.count - 1 {
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
