import SwiftUI

/// Actual V2 C-13 recorded teaching path, not a new set of generated Polish.
/// Each activity writes progress against the ORIGINAL source item ID.
struct GuidedFoundationsScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var navigation: LearningNavigation

    private let stages = [
        "First words",
        "Basic vocabulary",
        "First sentences / basic grammar"
    ]

    var body: some View {
        List {
            ForEach(stages, id: \.self) { stage in
                Section(stage) {
                    ForEach(learner.guidedFoundations.filter { $0.stage == stage }) { step in
                        Button {
                            navigation.openPractice(.guided(step.id))
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: step.isGrammar ? "textformat.abc" : "character.book.closed")
                                    .frame(width: 26)
                                    .foregroundStyle(.indigo)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(step.title).font(.body.weight(.medium))
                                    Text("\(learner.guidedPractisedCount(step)) of \(step.items.count) practised")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
        }
        .navigationTitle("Guided learning")
    }
}

/// First encounter is always Speak: hear the SOURCE recording, see its
/// existing English gloss, record/replay locally, then mark genuine practice.
/// If a group has three distinct original meanings, a second recap pass
/// requires an actual 3-choice Polish-to-English response. Neither audio
/// playback, a reveal, nor Skip can fabricate attempts or scores.
struct GuidedPracticeScreen: View {
    let step: GuidedFoundationStep

    @EnvironmentObject private var learner: LocalLearningStore
    @StateObject private var audio = NativeAudio()
    @State private var itemIndex = 0
    @State private var phase: GuidedExercisePhase = .introduce
    @State private var selectedOption: String?
    @State private var feedback: NativeSpeechFeedback?
    @State private var guideVisible = false
    @State private var finished = false
    @State private var speed: Float = 1

    private var current: GuidedRecordedItem { step.items[itemIndex] }
    private var source: LessonItem? { learner.sourceItem(for: current) }
    private var choices: [String] {
        GuidedExercisePlan.choices(for: step, index: itemIndex)
    }

    private var earlierPractice: [GuidedFoundationStep] {
        GuidedFoundationPath.prerequisitesToReview(
            for: step, in: learner.guidedFoundations,
            records: learner.profile.records)
    }

    private var following: NativeUnifiedJourneyNode? {
        learner.unifiedJourney?.next(after: .guided(step.id))
    }

    var body: some View {
        VStack(spacing: 14) {
            if finished {
                Spacer()
                ContentUnavailableView(
                    "End of activity", systemImage: "checkmark.circle",
                    description: Text("\(learner.guidedPractisedCount(step)) of \(step.items.count) original phrases practised. Unanswered recall checks remain available."))
                if let following {
                    NavigationLink(value: following.route) {
                        Label("Next: \(following.title)", systemImage: "arrow.right")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                }
                if let remaining = GuidedExercisePlan.nextPhase(
                    step: step, records: learner.profile.records) {
                    Button("Revisit unfinished practice") {
                        phase = remaining.0
                        itemIndex = remaining.1
                        finished = false
                        resetPresentation()
                        rememberPosition()
                    }
                    .buttonStyle(.bordered)
                }
                Button("Practise again") {
                    phase = .introduce
                    itemIndex = 0
                    finished = false
                    resetPresentation()
                    rememberPosition()
                }
                .buttonStyle(.bordered)
                if let error = learner.saveError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.footnote).foregroundStyle(.red)
                }
                Spacer()
            } else {
                HStack {
                    Text(step.stage).foregroundStyle(.secondary)
                    Spacer()
                    Text("\(itemIndex + 1) / \(step.items.count)")
                        .monospacedDigit().foregroundStyle(.secondary)
                }
                .font(.footnote)
                ProgressView(value: Double(itemIndex + 1),
                             total: Double(step.items.count))
                Label(phase == .introduce
                      ? "Speak · hear, understand, practise"
                      : "Learn · match the English meaning",
                      systemImage: phase == .introduce ? "mic" : "rectangle.on.rectangle")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        if !earlierPractice.isEmpty {
                            DisclosureGroup("Earlier learning to revisit (\(earlierPractice.count))") {
                                ForEach(earlierPractice) { earlier in
                                    NavigationLink {
                                        GuidedPracticeScreen(step: earlier)
                                    } label: {
                                        Label(earlier.title, systemImage: "arrow.uturn.backward")
                                    }
                                    .padding(.vertical, 4)
                                }
                            }
                            .font(.subheadline).foregroundStyle(.secondary)
                        }
                        if step.isGrammar {
                            Text(step.cue ?? "")
                                .font(.headline).foregroundStyle(.indigo)
                            Text(step.explanation ?? "")
                                .font(.body).foregroundStyle(.secondary)
                        }

                        VStack(alignment: .leading, spacing: 12) {
                            if phase == .introduce {
                                if feedback == nil {
                                    focusedPolish(current)
                                        .font(.largeTitle.weight(.semibold))
                                } else {
                                    NativeSpeechWord(polish: current.polish, feedback: feedback)
                                        .font(.largeTitle.weight(.semibold))
                                }
                                Text(current.english).font(.title3)
                                    .foregroundStyle(.secondary)
                            } else {
                                focusedPolish(current)
                                    .font(.largeTitle.weight(.semibold))
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(18)
                        .background(.quaternary.opacity(0.35),
                                    in: RoundedRectangle(cornerRadius: 16))

                        if let source {
                            HStack {
                                Button {
                                    audio.playReference(source, rate: speed)
                                } label: {
                                    Label("Hear Polish", systemImage: "play.circle.fill")
                                }
                                .buttonStyle(.bordered)
                                Picker("Speed", selection: $speed) {
                                    Text("0.75×").tag(Float(0.75))
                                    Text("1×").tag(Float(1))
                                }
                                .pickerStyle(.segmented)
                                .frame(maxWidth: 145)
                            }
                        }

                        if phase == .introduce {
                            speakControls
                        } else {
                            recapControls
                        }

                        if let message = audio.message {
                            Label(message, systemImage: "info.circle")
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                        if let error = learner.saveError {
                            Label(error, systemImage: "exclamationmark.triangle")
                                .font(.footnote).foregroundStyle(.red)
                        }
                    }
                    .padding(.vertical, 18)
                }

                HStack {
                    Button {
                        itemIndex -= 1
                    } label: {
                        Label("Back", systemImage: "chevron.left")
                    }
                    .disabled(itemIndex == 0)
                    Spacer()
                    Button("Skip") {
                        advance()
                    }
                    .buttonStyle(.bordered)
                    .accessibilityHint("No attempt or XP is awarded for skipping")
                }
                .padding(.bottom, 8)
            }
        }
        .padding(.horizontal)
        .navigationTitle(step.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if let pending = GuidedExercisePlan.nextPhase(
                step: step, records: learner.profile.records) {
                phase = pending.0
                itemIndex = pending.1
                if learner.guidedResumePhase(for: step.id) == phase,
                   let id = learner.guidedResumeItemID(for: step.id),
                   let i = step.items.firstIndex(where: { $0.id == id }) {
                    itemIndex = i
                }
            } else {
                finished = true
            }
            if !finished { rememberPosition() }
        }
        .onChange(of: itemIndex) { _, _ in
            resetPresentation()
            rememberPosition()
        }
        .onChange(of: phase) { _, _ in
            resetPresentation()
            rememberPosition()
        }
        .onDisappear { audio.discard() }
    }

    private var speakControls: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let pronunciation = source?.pronunciation, !pronunciation.isEmpty {
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
                    .buttonStyle(.borderedProminent).tint(.red)
                } else {
                    Button {
                        audio.requestRecord()
                    } label: {
                        Label(audio.hasRecording ? "Record again" : "Record", systemImage: "mic")
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(audio.isStarting)
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
            if audio.isStarting {
                ProgressView("Preparing microphone…")
            } else if audio.isRecording {
                Text("Recording… up to 10 seconds")
                    .foregroundStyle(.secondary)
            }
            if let source, audio.hasRecording && !audio.isRecording {
                NativeSpeechPracticePanel(item: source, audio: audio, feedback: $feedback)
                    .id(source.id)
                Button("Mark practised") {
                    NativePracticeSubmission.commit(
                        store: learner, item: source, mode: .speak,
                        understood: nil) {
                            advance()
                        }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!audio.usableRecording)
            }
        }
    }

    private var recapControls: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Choose the English meaning")
                .font(.headline)
            ForEach(choices, id: \.self) { option in
                Button {
                    guard selectedOption == nil, let source else { return }
                    NativePracticeSubmission.commit(
                        store: learner, item: source, mode: .learn,
                        understood: option == current.english,
                        evidence: .matching) {
                            selectedOption = option
                        }
                } label: {
                    HStack {
                        Text(option).multilineTextAlignment(.leading)
                        Spacer()
                        if selectedOption == option {
                            Image(systemName: option == current.english
                                  ? "checkmark.circle.fill" : "xmark.circle.fill")
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.bordered)
                .disabled(selectedOption != nil)
            }
            if let selectedOption {
                Label(selectedOption == current.english ? "Correct" : "Needs practice",
                      systemImage: selectedOption == current.english
                      ? "checkmark.circle" : "arrow.clockwise")
                Text("Meaning: " + current.english)
                    .foregroundStyle(.secondary)
                Button(itemIndex + 1 < step.items.count ? "Next word" : "Finish recap") {
                    advance()
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private func focusedPolish(_ item: GuidedRecordedItem) -> Text {
        guard let focus = item.focus, let range = item.polish.range(of: focus) else {
            return Text(item.polish)
        }
        return Text(String(item.polish[..<range.lowerBound]))
            + Text(focus).bold().foregroundColor(.indigo)
            + Text(String(item.polish[range.upperBound...]))
    }

    private func advance() {
        guard itemIndex + 1 < step.items.count else {
            if phase == .introduce && GuidedExercisePlan.hasRecap(step) {
                phase = .recap
                itemIndex = 0
                return
            }
            guard learner.finishedGuidedStep(step.id) else { return }
            audio.discard()
            finished = true
            return
        }
        itemIndex += 1
    }

    private func resetPresentation() {
        audio.discard()
        feedback = nil
        selectedOption = nil
        guideVisible = false
    }

    private func rememberPosition() {
        guard !finished else { return }
        learner.rememberGuidedPosition(stepID: step.id,
                                       itemID: current.id, phase: phase)
    }
}
