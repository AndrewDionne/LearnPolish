import SwiftUI

struct AppShell: View {
    var body: some View {
        TabView {
            NavigationStack { HomeScreen() }
                .tabItem { Label("Home", systemImage: "house") }
            NavigationStack { LibraryScreen() }
                .tabItem { Label("Library", systemImage: "books.vertical") }
            NavigationStack { ReviewScreen() }
                .tabItem { Label("Practice", systemImage: "rectangle.stack") }
            NavigationStack { PolandExpeditionView() }
                .tabItem { Label("Expedition", systemImage: "map") }
            NavigationStack { ProgressScreen() }
                .tabItem { Label("Progress", systemImage: "chart.bar") }
        }
        .tint(.indigo)
    }
}

struct HomeScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Path to Polish")
                    .font(.largeTitle.bold())
                Text("Learn real Polish, one lesson at a time.")
                    .foregroundStyle(.secondary)

                if let message = learner.catalogError {
                    ContentUnavailableView("Lessons unavailable", systemImage: "exclamationmark.triangle",
                                           description: Text(message))
                } else {
                    if let guided = learner.nextGuidedStep {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Continue guided learning")
                                .font(.headline)
                            Text(guided.title)
                                .font(.title2.weight(.semibold))
                            Text(guided.stage)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            NavigationLink {
                                GuidedPracticeScreen(step: guided)
                            } label: {
                                Label("Continue", systemImage: "arrow.right")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        .padding(18)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.quaternary.opacity(0.4),
                                    in: RoundedRectangle(cornerRadius: 18))
                    }

                    NavigationLink {
                        GuidedFoundationsScreen()
                    } label: {
                        Label("First words, grammar and sentences",
                              systemImage: "text.book.closed")
                    }
                    .font(.headline)

                    NavigationLink {
                        SoundStudioScreen()
                    } label: {
                        Label("Polish alphabet and sound practice",
                              systemImage: "waveform")
                    }
                    .font(.headline)
                    NavigationLink {
                        TouristUnitsScreen()
                    } label: {
                        Label("Everyday Polish scenarios",
                              systemImage: "figure.walk")
                    }
                    .font(.headline)

                    if let scenario = learner.nextTouristUnit {
                        HStack {
                            Text("Next scenario")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Spacer()
                            NavigationLink(scenario.title) {
                                TouristUnitScreen(unit: scenario)
                            }
                            .font(.subheadline.weight(.medium))
                        }
                    }


                    if let lesson = learner.nextLesson {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Continue learning")
                                .font(.headline)
                            Text(lesson.title)
                                .font(.title2.weight(.semibold))
                            if let description = lesson.description {
                                Text(description).foregroundStyle(.secondary)
                            }
                            NavigationLink {
                                LessonScreen(lesson: lesson, resumeAtNextUnseen: true)
                            } label: {
                                Label("Continue", systemImage: "arrow.right")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        .padding(18)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 18))
                    }

                    Text("Your path")
                        .font(.headline)
                    ForEach(learner.course) { lesson in
                        NavigationLink {
                            LessonScreen(lesson: lesson)
                        } label: {
                            LessonRow(lesson: lesson)
                        }
                        .buttonStyle(.plain)
                        Divider()
                    }
                }
                if let error = learner.saveError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }
            .padding()
        }
        .navigationTitle("Home")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct LibraryScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @State private var query = ""

    private func matching(_ entries: [Lesson]) -> [Lesson] {
        guard !query.isEmpty else { return entries }
        return entries.filter {
            $0.title.localizedCaseInsensitiveContains(query) ||
            ($0.description?.localizedCaseInsensitiveContains(query) ?? false)
        }
    }

    var body: some View {
        List {
            Section("Foundations") {
                NavigationLink {
                    GuidedFoundationsScreen()
                } label: {
                    Label("First words and basic grammar", systemImage: "text.book.closed")
                }
                NavigationLink {
                    SoundStudioScreen()
                } label: {
                    Label("Alphabet and Sound Lab", systemImage: "waveform")
                }
                NavigationLink {
                    TouristUnitsScreen()
                } label: {
                    Label("Everyday scenarios", systemImage: "figure.walk")
                }
            }
            if learner.catalogError != nil {
                Text(learner.catalogError ?? "").foregroundStyle(.red)
            }
            if !matching(learner.course).isEmpty {
                Section("Your path") {
                    ForEach(matching(learner.course)) { lesson in
                        NavigationLink {
                            LessonScreen(lesson: lesson)
                        } label: {
                            LessonRow(lesson: lesson)
                        }
                    }
                }
            }
            if !matching(learner.explore).isEmpty {
                Section("Explore more") {
                    ForEach(matching(learner.explore)) { lesson in
                        NavigationLink {
                            LessonScreen(lesson: lesson)
                        } label: {
                            LessonRow(lesson: lesson)
                        }
                    }
                }
            }
        }
        .searchable(text: $query, prompt: "Find a lesson")
        .navigationTitle("Library")
    }
}

struct LessonRow: View {
    let lesson: Lesson

    private var symbol: String {
        switch lesson.kind {
        case "sounds": return "waveform"
        case "reading": return "text.book.closed"
        default: return "character.book.closed"
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: symbol)
                .font(.title3)
                .foregroundStyle(lesson.stageRank == 0 ? .teal : (lesson.stageRank == 1 ? .indigo : .orange))
                .frame(width: 34, height: 42)
            VStack(alignment: .leading, spacing: 3) {
                Text(lesson.title)
                    .font(.body.weight(.semibold))
                Text("\(lesson.items.count) items")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .contentShape(Rectangle())
        .padding(.vertical, 5)
    }
}

private struct DueReviewGroup: Identifiable {
    let lesson: Lesson
    let items: [LessonItem]
    var id: String { lesson.id }
}

struct ReviewScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore

    private var dueGroups: [DueReviewGroup] {
        learner.lessons.filter { $0.kind != "reading" }.compactMap { lesson in
            let due = lesson.items.filter { item in
                guard let at = learner.record(for: item, mode: .learn).nextReview else { return false }
                return at <= Date()
            }
            return due.isEmpty ? nil : DueReviewGroup(lesson: lesson, items: due)
        }
    }

    var body: some View {
        List {
            if dueGroups.isEmpty {
                ContentUnavailableView("Nothing due yet", systemImage: "checkmark.circle",
                                       description: Text("Practise a lesson to start your review schedule."))
            } else {
                Section("Scheduled review") {
                    ForEach(dueGroups) { group in
                        NavigationLink {
                            // Frozen list: failed items remain due later but never trap
                            // the learner in an endless same-session review loop.
                            LessonScreen(lesson: group.lesson, preferredMode: .learn,
                                         dueItemIDs: group.items.map(\.id))
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(group.lesson.title).font(.headline)
                                Text("\(group.items.count) due")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("Practice")
    }
}

struct ProgressScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore

    var body: some View {
        Form {
            Section("On this iPhone") {
                LabeledContent("Items studied", value: "\(learner.completedItems)")
                LabeledContent("Practice attempts", value: "\(learner.attempts)")
                LabeledContent("Reviews due", value: "\(learner.dueReviews.count)")
                LabeledContent("Personal XP", value: "\(learner.expedition.totalXP)")
            }
            Section("Storage") {
                Label("Learning works offline", systemImage: "iphone")
                Text("Progress is saved privately on this device. Cloud backup and family groups are not yet connected in V3.")
                    .foregroundStyle(.secondary)
                if let error = learner.saveError {
                    Text(error).foregroundStyle(.red)
                }
            }
            Section("Account") {
                Text("No account is needed to learn.")
                Text("Optional sync and group invitations will be added after privacy and sharing tests.")
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("My progress")
    }
}
