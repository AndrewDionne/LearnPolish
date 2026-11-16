import SwiftUI

/// A browse-only view of one source-validated Journey 1. Lesson screens
/// belong in Practice; opening any activity switches to that tab.
/// No locks, synthetic grade or duplicated lesson / source item is created.
struct NativeUnifiedJourneyOverviewScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var navigation: LearningNavigation

    var body: some View {
        List {
            if let journey = learner.unifiedJourney,
               let core = learner.coreJourney {
                Section {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("First words to practical conversations")
                            .font(.title3.weight(.semibold))
                        let complete = learner.unifiedJourneyStepsCompleted
                        let count = learner.unifiedJourneyStepsTotal
                        ProgressView(value: Double(complete),
                                     total: Double(max(count, 1)))
                        Text("\(complete) of \(count) activities practised")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        if let next = journey.nextUnpractised(
                            guided: learner.guidedFoundations, core: core,
                            records: learner.profile.records) {
                            Button {
                                navigation.openPractice(next.route)
                            } label: {
                                Label("Continue: \(next.title)", systemImage: "arrow.right")
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.borderedProminent)
                        } else {
                            Label("Every activity has a saved attempt",
                                  systemImage: "checkmark.circle")
                        }
                    }
                    .padding(.vertical, 5)
                }
                ForEach(Array(journey.chapters.enumerated()), id: \.element.id) { pair in
                    let chapter = pair.element
                    Section("Chapter \(pair.offset + 1)") {
                        NavigationLink {
                            NativeUnifiedJourneyChapterScreen(chapter: chapter)
                        } label: {
                            let progress = journey.progress(
                                chapter, guided: learner.guidedFoundations,
                                core: core, records: learner.profile.records)
                            VStack(alignment: .leading, spacing: 7) {
                                Text(chapter.title).font(.headline)
                                Text(chapter.description)
                                    .font(.subheadline).foregroundStyle(.secondary)
                                ProgressView(value: Double(progress.practised),
                                             total: Double(max(chapter.nodes.count, 1)))
                                HStack {
                                    Text("\(progress.practised) / \(chapter.nodes.count) practised")
                                    Spacer()
                                    if let accuracy = journey.matchingAccuracy(
                                        for: chapter, records: learner.profile.records) {
                                        Text("Matching \(accuracy)%")
                                    } else {
                                        Text("\(progress.started) started")
                                    }
                                }
                                .font(.caption).foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 5)
                        }
                    }
                }
            } else {
                ContentUnavailableView("Journey unavailable",
                                       systemImage: "exclamationmark.triangle",
                                       description: Text(learner.catalogError ??
                                                         "Source validation has not completed."))
            }
        }
        .navigationTitle("Journey 1")
    }
}

struct NativeUnifiedJourneyChapterScreen: View {
    let chapter: NativeUnifiedJourneyChapter

    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var navigation: LearningNavigation

    var body: some View {
        List {
            Section {
                Text(chapter.description).foregroundStyle(.secondary)
                if let journey = learner.unifiedJourney,
                   let core = learner.coreJourney {
                    let progress = journey.progress(
                        chapter, guided: learner.guidedFoundations,
                        core: core, records: learner.profile.records)
                    LabeledContent("Activities practised",
                                   value: "\(progress.practised) / \(chapter.nodes.count)")
                    if let matching = journey.matchingAccuracy(
                        for: chapter, records: learner.profile.records) {
                        LabeledContent("Matching accuracy", value: "\(matching)%")
                    } else {
                        Text("Matching accuracy is not assessed yet")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            Section("Learning activities") {
                ForEach(chapter.nodes) { node in
                    Button {
                        navigation.openPractice(node.route)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: node.route.isGuided
                                  ? "character.book.closed" : "book")
                                .foregroundStyle(.indigo)
                                .frame(width: 24)
                            VStack(alignment: .leading, spacing: 5) {
                                Text(node.title).font(.headline)
                                    .foregroundStyle(.primary)
                                Text(node.descriptor)
                                    .font(.caption).foregroundStyle(.secondary)
                                if let journey = learner.unifiedJourney,
                                   let core = learner.coreJourney {
                                    let progress = journey.progress(
                                        node, guided: learner.guidedFoundations,
                                        core: core, records: learner.profile.records)
                                    Text(progress.complete ? "Practised" :
                                         progress.started ? "In progress" : "Not yet practised")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 7)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .navigationTitle(chapter.title)
    }
}

private extension PracticeRoute {
    var isGuided: Bool {
        if case .guided = self { return true }
        return false
    }
}
