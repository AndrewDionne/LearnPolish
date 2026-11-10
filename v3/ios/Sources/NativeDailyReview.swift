import SwiftUI

/// Frozen, source-backed spaced-review card from the existing V2 Learn
/// contract. A single session never recomputes the due queue after an
/// answer: misses stay due but are not repeated endlessly within a session.
struct NativeDailyReviewCard: Identifiable {
    let lesson: Lesson
    let item: LessonItem
    let dueAt: Date

    var id: String { item.id }
}

enum NativeDailyReviewQueue {
    static let batchLimit = 20

    /// Oldest-due first, stable source order for ties. No unseen items,
    /// reading-only content, Speak scores, or inferred completions.
    static func snapshot(lessons: [Lesson], records: [String: PracticeRecord],
                         now: Date, limit: Int = batchLimit)
        -> [NativeDailyReviewCard] {
        guard limit > 0 else { return [] }
        let entries: [(lessonIndex: Int, itemIndex: Int,
                       card: NativeDailyReviewCard)] = lessons.enumerated()
            .flatMap { lessonIndex, lesson in
                guard lesson.kind != "reading",
                      lesson.availableModes.contains(.learn) else {
                    return [(Int, Int, NativeDailyReviewCard)]()
                }
                return lesson.items.enumerated().compactMap { itemIndex, item in
                    guard let record = records["learn:" + item.id],
                          let dueAt = record.nextReview,
                          dueAt.timeIntervalSince1970.isFinite,
                          record.attempts > 0, dueAt <= now else { return nil }
                    return (lessonIndex, itemIndex,
                            NativeDailyReviewCard(lesson: lesson, item: item,
                                                  dueAt: dueAt))
                }
            }
        return entries.sorted {
            if $0.card.dueAt != $1.card.dueAt {
                return $0.card.dueAt < $1.card.dueAt
            }
            if $0.lessonIndex != $1.lessonIndex {
                return $0.lessonIndex < $1.lessonIndex
            }
            return $0.itemIndex < $1.itemIndex
        }.prefix(min(limit, batchLimit)).map(\.card)
    }
}

/// One short cross-lesson review queue. Only committed responses count;
/// Skip is explicit and non-awarding. All words and audio are original
/// local curriculum assets. No authentication or network request.
struct NativeDailyReviewSessionScreen: View {
    let cards: [NativeDailyReviewCard]

    @EnvironmentObject private var learner: LocalLearningStore
    @Environment(\.dismiss) private var dismiss
    @StateObject private var audio = NativeAudio()
    @State private var index = 0
    @State private var revealed = false
    @State private var playbackRate: Float = 1
    @State private var reviewed = 0
    @State private var needsPractice = 0

    private var current: NativeDailyReviewCard? {
        cards.indices.contains(index) ? cards[index] : nil
    }

    var body: some View {
        VStack(spacing: 16) {
            if let current {
                HStack {
                    Text("\(index + 1) / \(cards.count)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(current.lesson.title)
                        .font(.subheadline)
                        .lineLimit(1)
                        .foregroundStyle(.secondary)
                }
                ProgressView(value: Double(index + 1), total: Double(cards.count))
                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        Text(current.item.polish)
                            .font(.largeTitle.weight(.semibold))
                            .textSelection(.enabled)
                        if current.item.audio != nil {
                            HStack {
                                Button {
                                    audio.playReference(current.item,
                                                        rate: playbackRate)
                                } label: {
                                    Label("Hear Polish", systemImage: "play.circle.fill")
                                }
                                .buttonStyle(.bordered)
                                Picker("Speed", selection: $playbackRate) {
                                    Text("0.75×").tag(Float(0.75))
                                    Text("1×").tag(Float(1))
                                }
                                .pickerStyle(.segmented)
                                .frame(maxWidth: 145)
                            }
                        }
                        if revealed {
                            Text(current.item.english)
                                .font(.title3)
                            HStack(spacing: 12) {
                                Button("Needs practice") {
                                    submit(current.item, understood: false)
                                }
                                .buttonStyle(.bordered)
                                Button("Got it") {
                                    submit(current.item, understood: true)
                                }
                                .buttonStyle(.borderedProminent)
                            }
                        } else {
                            Button("Show meaning") { revealed = true }
                                .buttonStyle(.borderedProminent)
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
                    .padding(.vertical, 24)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                HStack {
                    Text("Review: \(reviewed)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button("Skip") { advance() }
                        .accessibilityHint("Move on without recording an answer or earning XP")
                }
                .padding(.bottom, 8)
            } else {
                Spacer()
                ContentUnavailableView(
                    "Review finished", systemImage: "checkmark.circle",
                    description: Text("\(reviewed) answers saved. \(needsPractice) marked for further practice."))
                Text("Cards needing practice or skipped remain in the regular review schedule.")
                    .font(.footnote).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Button("Done") { dismiss() }
                    .buttonStyle(.borderedProminent)
                Spacer()
            }
        }
        .padding(.horizontal)
        .navigationTitle("Daily review")
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { audio.discard() }
    }

    private func submit(_ item: LessonItem, understood: Bool) {
        NativePracticeSubmission.commit(
            store: learner, item: item, mode: .learn,
            understood: understood) {
                reviewed += 1
                if !understood { needsPractice += 1 }
                advance()
            }
    }

    private func advance() {
        audio.discard()
        revealed = false
        index += 1
    }
}
