import SwiftUI

/// A source-authored two- to four-turn exchange. Each turn uses its own
/// original bundled MP3; the question is the exact authored V2 question.
/// There is no generated speech, unreviewed distractor or artificial score.
struct NativeDialoguePracticeScreen: View {
    let lesson: Lesson

    @EnvironmentObject private var learner: LocalLearningStore
    @StateObject private var audio = NativeAudio()
    @State private var sceneIndex = 0
    @State private var selectedAnswer: String?
    @State private var finished = false
    @State private var speed: Float = 1

    private var scenes: [NativeMicroDialogue] { lesson.microDialogues ?? [] }
    private var scene: NativeMicroDialogue? {
        scenes.indices.contains(sceneIndex) ? scenes[sceneIndex] : nil
    }

    private func original(_ id: String) -> LessonItem? {
        lesson.items.first(where: { $0.id == id })
    }

    var body: some View {
        VStack(spacing: 14) {
            if finished {
                Spacer()
                ContentUnavailableView("Dialogue practice finished",
                                       systemImage: "checkmark.circle",
                                       description: Text("Only your answered questions were recorded."))
                Button("Practise these dialogues again") {
                    finished = false
                    sceneIndex = 0
                    selectedAnswer = nil
                }
                .buttonStyle(.borderedProminent)
                if let following = learner.unifiedJourney?.next(after: .lesson(lesson.id)) {
                    NavigationLink(value: following.route) {
                        Label("Next: \(following.title)", systemImage: "arrow.right")
                    }
                    .buttonStyle(.bordered)
                }
                Spacer()
            } else if let scene {
                HStack {
                    Text("Listen · \(scene.title)")
                        .font(.headline)
                    Spacer()
                    Text("\(sceneIndex + 1) / \(scenes.count)")
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                }
                ProgressView(value: Double(sceneIndex + 1),
                             total: Double(scenes.count))
                ScrollView {
                    VStack(alignment: .leading, spacing: 17) {
                        Text("Hear the speakers in order, then answer what happened.")
                            .foregroundStyle(.secondary)
                        ForEach(Array(scene.turns.enumerated()), id: \.offset) { entry in
                            let index = entry.offset
                            let turn = entry.element
                            if let item = original(turn.itemId) {
                                Button {
                                    audio.playReference(item, rate: speed)
                                } label: {
                                    Label("Play speaker \(turn.speaker) · turn \(index + 1)",
                                          systemImage: "play.circle.fill")
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                                .buttonStyle(.bordered)
                            }
                        }
                        Picker("Speed", selection: $speed) {
                            Text("0.75×").tag(Float(0.75))
                            Text("1×").tag(Float(1))
                        }
                        .pickerStyle(.segmented)
                        .frame(maxWidth: 220)
                        Text(scene.comprehension.prompt).font(.title3.bold())
                        ForEach(scene.comprehension.options, id: \.self) { option in
                            Button {
                                answer(option, scene: scene)
                            } label: {
                                HStack {
                                    Text(option).multilineTextAlignment(.leading)
                                    Spacer()
                                    if selectedAnswer == option {
                                        Image(systemName: correct(option, scene: scene)
                                              ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.bordered)
                            .disabled(selectedAnswer != nil)
                        }
                        if let selectedAnswer {
                            Label(correct(selectedAnswer, scene: scene)
                                  ? "Correct" : "Needs practice",
                                  systemImage: correct(selectedAnswer, scene: scene)
                                  ? "checkmark.circle" : "arrow.clockwise")
                            Text(scene.comprehension.feedback)
                                .foregroundStyle(.secondary)
                            Text("Dialogue transcript").font(.headline)
                            ForEach(scene.turns, id: \.itemId) { turn in
                                if let item = original(turn.itemId) {
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text("Speaker \(turn.speaker) · " + item.polish)
                                        Text(item.english)
                                            .foregroundStyle(.secondary)
                                    }
                                    .font(.subheadline)
                                }
                            }
                        }
                        if let message = audio.message {
                            Text(message).font(.footnote).foregroundStyle(.secondary)
                        }
                        if let error = learner.saveError {
                            Text(error).font(.footnote).foregroundStyle(.red)
                        }
                    }
                    .padding(.vertical, 10)
                }
                HStack {
                    Text(selectedAnswer == nil
                         ? "Listening or reading does not award XP."
                         : "Answer saved on this iPhone.")
                        .font(.footnote).foregroundStyle(.secondary)
                    Spacer()
                    Button(sceneIndex + 1 < scenes.count ? "Next dialogue" : "Finish") {
                        advance()
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedAnswer == nil)
                }
            } else {
                ContentUnavailableView("No verified dialogue",
                                       systemImage: "exclamationmark.triangle")
            }
        }
        .padding(.horizontal)
        .navigationTitle(lesson.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if let cursor = learner.practiceCursor(for: lesson.id),
               let position = scenes.firstIndex(where: {
                   $0.turns.last?.itemId == cursor.itemID }) {
                sceneIndex = position
            }
            remember()
        }
        .onChange(of: sceneIndex) { _, _ in
            selectedAnswer = nil
            audio.discard()
            remember()
        }
        .onDisappear { audio.discard() }
    }

    private func correct(_ answer: String, scene: NativeMicroDialogue) -> Bool {
        scene.comprehension.options.indices.contains(scene.comprehension.correctIndex) &&
            answer == scene.comprehension.options[scene.comprehension.correctIndex]
    }

    private func answer(_ option: String, scene: NativeMicroDialogue) {
        guard selectedAnswer == nil,
              scene.comprehension.options.contains(option),
              let last = scene.turns.last,
              let item = original(last.itemId) else { return }
        NativePracticeSubmission.commit(
            store: learner, item: item, mode: .listen,
            understood: correct(option, scene: scene), evidence: .dialogue) {
                selectedAnswer = option
            }
    }

    private func remember() {
        guard !finished, let last = scene?.turns.last,
              let item = original(last.itemId) else { return }
        learner.rememberPosition(lesson: lesson, item: item, mode: .listen)
    }

    private func advance() {
        guard selectedAnswer != nil else { return }
        if scenes.indices.contains(sceneIndex + 1) {
            sceneIndex += 1
        } else {
            finished = true
            audio.discard()
        }
    }
}
