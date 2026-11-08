import SwiftUI

struct TouristUnitsScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore

    private func completedCount(for unit: TouristUnit) -> Int {
        unit.steps.indices.filter { learner.touristStepComplete(unit: unit, index: $0) }.count
    }

    var body: some View {
        List {
            Section {
                Text("Listen, speak and read using original Polish recordings.")
                    .foregroundStyle(.secondary)
            }
            ForEach(learner.touristUnits) { unit in
                NavigationLink {
                    TouristUnitScreen(unit: unit)
                } label: {
                    HStack(spacing: 12) {
                        Text(String(format: "%02d", unit.order))
                            .font(.headline.monospacedDigit())
                            .foregroundStyle(.indigo)
                            .frame(width: 34)
                        VStack(alignment: .leading, spacing: 5) {
                            Text(unit.title).font(.headline)
                            Text(unit.outcome)
                                .font(.subheadline).foregroundStyle(.secondary)
                            Text("\(completedCount(for: unit)) of \(unit.steps.count) stages practised")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 5)
                }
            }
        }
        .navigationTitle("Everyday Polish")
    }
}

struct TouristUnitScreen: View {
    let unit: TouristUnit
    @EnvironmentObject private var learner: LocalLearningStore

    private var nextStep: Int {
        if learner.touristProgress.unitID == unit.id,
           unit.steps.indices.contains(learner.touristProgress.stepIndex),
           !learner.touristStepComplete(unit: unit,
                                        index: learner.touristProgress.stepIndex) {
            return learner.touristProgress.stepIndex
        }
        return unit.steps.indices.first {
            !learner.touristStepComplete(unit: unit, index: $0)
        } ?? 0
    }

    var body: some View {
        List {
            Section {
                Text(unit.outcome).font(.body)
                NavigationLink {
                    TouristStepScreen(unit: unit, stepIndex: nextStep)
                } label: {
                    Label("Continue", systemImage: "arrow.right")
                        .font(.headline)
                }
            }
            Section("Practice stages") {
                ForEach(unit.steps.indices, id: \.self) { index in
                    NavigationLink {
                        TouristStepScreen(unit: unit, stepIndex: index)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: unit.steps[index].mode.symbol)
                                .foregroundStyle(.indigo)
                                .frame(width: 28)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(unit.steps[index].mode.label)
                                    .font(.headline)
                                Text(unit.steps[index].title)
                                    .font(.caption).foregroundStyle(.secondary)
                                Text("\(learner.touristStepAttemptCount(unit: unit, index: index)) / \(unit.steps[index].items.count) practised")
                                    .font(.caption2).foregroundStyle(.secondary)
                            }
                            Spacer()
                            if learner.touristStepComplete(unit: unit, index: index) {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.teal)
                            }
                        }
                        .padding(.vertical, 5)
                    }
                }
            }
        }
        .navigationTitle(unit.title)
    }
}

/// A tourist stage remains navigable even if earlier stages were skipped. XP
/// and completion require real recorded/answered attempts, not source preview.
struct TouristStepScreen: View {
    let unit: TouristUnit
    let stepIndex: Int

    @EnvironmentObject private var learner: LocalLearningStore
    @StateObject private var audio = NativeAudio()
    @State private var index = 0
    @State private var playbackRate: Float = 1
    @State private var showingIntroduction = false
    @State private var revealed = false
    @State private var selected: String?
    @State private var finished = false
    @State private var completed = false

    private var step: TouristStep { unit.steps[stepIndex] }
    private var item: TouristRecordedItem { step.items[index] }

    private var sourceIntroduction: NativeSourceIntroLesson {
        step.sourceIntroduction(from: learner.sourceExposure)
    }

    private var choices: [String] {
        if let check = item.comprehension, step.mode == .read {
            return check.options
        }
        var values = [item.english]
        for other in step.items where other.id != item.id {
            if !values.contains(other.english) { values.append(other.english) }
            if values.count >= 3 { break }
        }
        return values.sorted()
    }

    private var correctAnswer: String {
        if let check = item.comprehension, step.mode == .read,
           check.options.indices.contains(check.correctIndex) {
            return check.options[check.correctIndex]
        }
        return item.english
    }

    var body: some View {
        VStack(spacing: 12) {
            if finished {
                Spacer()
                ContentUnavailableView(completed ? "Stage practised" : "Stage not complete",
                    systemImage: completed ? "checkmark.circle" : "arrow.uturn.backward",
                    description: Text(completed
                        ? "Your practice is saved on this iPhone."
                        : "You can continue exploring. Unpractised items are not marked complete."))
                if unit.steps.indices.contains(stepIndex + 1) {
                    NavigationLink {
                        TouristStepScreen(unit: unit, stepIndex: stepIndex + 1)
                    } label: {
                        Label("Next: \(unit.steps[stepIndex + 1].mode.label)",
                              systemImage: "arrow.right")
                    }
                    .buttonStyle(.borderedProminent)
                } else if let following = learner.touristUnits.first(where: { $0.order == unit.order + 1 }) {
                    NavigationLink {
                        TouristUnitScreen(unit: following)
                    } label: {
                        Label("Next scenario", systemImage: "arrow.right")
                    }
                    .buttonStyle(.borderedProminent)
                }
                Button("Practise this stage again") {
                    finished = false
                    index = step.items.firstIndex(where: { original in
                        !(learner.touristProgress.attemptedByStep[
                          LocalTouristProgress.key(unitID: unit.id, stepIndex: stepIndex)] ?? [])
                          .contains(original.id)
                    }) ?? 0
                    resetCard()
                    remember()
                }
                .buttonStyle(.bordered)
                Spacer()
            } else if showingIntroduction && step.mode != .speak {
                SourceFirstIntroductionView(introduction: sourceIntroduction) {
                    showingIntroduction = false
                }
            } else {
                HStack {
                    Label(step.mode.label, systemImage: step.mode.symbol)
                        .font(.subheadline)
                    Spacer()
                    Text("\(index + 1) / \(step.items.count)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                ProgressView(value: Double(index + 1), total: Double(step.items.count))
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        switch step.mode {
                        case .listen: listenActivity
                        case .speak: speakActivity
                        case .read: readActivity
                        case .learn: EmptyView()
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
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 16)
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
                        advance()
                    } label: {
                        Label(index == step.items.count - 1 ? "Finish stage" : "Next",
                              systemImage: "chevron.right")
                    }
                    .buttonStyle(.borderedProminent)
                    .accessibilityHint("Unanswered items are left incomplete")
                }
            }
        }
        .padding(.horizontal)
        .navigationTitle(unit.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if learner.touristProgress.unitID == unit.id &&
               learner.touristProgress.stepIndex == stepIndex,
               let remembered = learner.touristProgress.itemID,
               let position = step.items.firstIndex(where: { $0.id == remembered }) {
                index = position
            } else {
                index = step.items.firstIndex(where: {
                    !(learner.touristProgress.attemptedByStep[
                        LocalTouristProgress.key(unitID: unit.id, stepIndex: stepIndex)] ?? [])
                        .contains($0.id)
                }) ?? 0
            }
            showingIntroduction = step.mode != .speak &&
                learner.touristStepAttemptCount(unit: unit, index: stepIndex) == 0
            remember()
        }
        .onChange(of: index) { _, _ in resetCard(); remember() }
        .onDisappear { audio.discard() }
    }

    @ViewBuilder
    private var listenActivity: some View {
        Text("Listen to the original Polish recording.")
            .font(.headline)
        playback
        if selected == nil && !revealed {
            if choices.count >= 2 {
                Text("Choose the meaning.")
                options
            } else {
                Button("Show meaning") { revealed = true }
                    .buttonStyle(.bordered)
            }
        }
        if selected != nil || revealed {
            Text(item.polish).font(.title2.bold()).textSelection(.enabled)
            Text(item.english).font(.title3)
            if selected == nil { ratingControls }
        }
    }

    @ViewBuilder
    private var readActivity: some View {
        Text(item.polish).font(.title2.bold()).textSelection(.enabled)
        playback
        if let check = item.comprehension,
           check.options.indices.contains(check.correctIndex) {
            Text(check.prompt).font(.headline)
            options
            if selected != nil {
                Text(item.english).foregroundStyle(.secondary)
                Text(check.feedback).font(.footnote).foregroundStyle(.secondary)
            }
        } else if revealed {
            Text(item.english).font(.title3)
            ratingControls
        } else {
            Button("Show meaning") { revealed = true }
                .buttonStyle(.bordered)
        }
    }

    private var speakActivity: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(item.polish).font(.title2.bold()).textSelection(.enabled)
            Text(item.english).font(.body).foregroundStyle(.secondary)
            playback
            HStack {
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
            if audio.hasRecording && !audio.isRecording {
                if let original = learner.originalTouristItem(item.id, unit: unit, stepIndex: stepIndex) {
                    NativeSpeechPracticePanel(item: original, audio: audio)
                        .id(item.id)
                }
                Button("Mark practised") {
                    learner.recordTouristAttempt(unit: unit, stepIndex: stepIndex,
                                                itemID: item.id, understood: nil)
                    advance()
                }
                .buttonStyle(.borderedProminent)
            }
            Text("Recordings stay on this iPhone unless you explicitly authorize a connected pronunciation check.")
                .font(.footnote).foregroundStyle(.secondary)
        }
    }

    private var playback: some View {
        HStack(spacing: 12) {
            Button {
                audio.playFile(item.audio, rate: playbackRate)
            } label: {
                Label("Hear Polish", systemImage: "play.circle.fill")
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

    private var options: some View {
        ForEach(choices, id: \.self) { answer in
            Button {
                guard selected == nil else { return }
                selected = answer
                learner.recordTouristAttempt(unit: unit, stepIndex: stepIndex,
                                            itemID: item.id, understood: answer == correctAnswer)
            } label: {
                HStack {
                    Text(answer)
                        .multilineTextAlignment(.leading)
                    Spacer()
                    if selected == answer {
                        Image(systemName: answer == correctAnswer ? "checkmark.circle" : "xmark.circle")
                    }
                }
            }
            .buttonStyle(.bordered)
            .disabled(selected != nil)
        }
    }

    private var ratingControls: some View {
        HStack {
            Button("Needs practice") { rate(false) }
                .buttonStyle(.bordered)
            Button("Understood") { rate(true) }
                .buttonStyle(.borderedProminent)
        }
    }

    private func rate(_ understood: Bool) {
        learner.recordTouristAttempt(unit: unit, stepIndex: stepIndex,
                                    itemID: item.id, understood: understood)
        advance()
    }

    private func advance() {
        audio.discard()
        if index + 1 < step.items.count {
            index += 1
        } else {
            completed = learner.finishTouristStep(unit: unit, stepIndex: stepIndex)
            finished = true
        }
    }

    private func resetCard() {
        audio.discard()
        revealed = false
        selected = nil
    }

    private func remember() {
        guard !finished else { return }
        learner.rememberTouristPosition(unit: unit, stepIndex: stepIndex,
                                        itemID: item.id)
    }
}
