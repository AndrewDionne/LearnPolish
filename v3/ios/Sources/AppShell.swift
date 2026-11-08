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
                                LessonScreen(lesson: lesson)
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

                    Text("Your learning path")
                        .font(.headline)
                    ForEach(learner.course.prefix(8)) { lesson in
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

    var filtered: [Lesson] {
        guard !query.isEmpty else { return learner.lessons }
        return learner.lessons.filter {
            $0.title.localizedCaseInsensitiveContains(query) ||
            ($0.description?.localizedCaseInsensitiveContains(query) ?? false)
        }
    }

    var body: some View {
        List(filtered) { lesson in
            NavigationLink {
                LessonScreen(lesson: lesson)
            } label: {
                LessonRow(lesson: lesson)
            }
        }
        .overlay {
            if filtered.isEmpty {
                ContentUnavailableView("No lessons", systemImage: "text.book.closed",
                                       description: Text(learner.catalogError ?? "Try another search."))
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

struct ReviewScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore

    var body: some View {
        List {
            if learner.dueReviews.isEmpty {
                ContentUnavailableView("Nothing due yet", systemImage: "checkmark.circle",
                                       description: Text("Practise a lesson to start your review schedule."))
            } else {
                ForEach(learner.dueReviews, id: \.1.id) { pair in
                    NavigationLink {
                        LessonScreen(lesson: pair.0, startItemID: pair.1.id,
                                     preferredMode: .learn)
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(pair.1.polish).font(.headline)
                            Text(pair.0.title).font(.caption).foregroundStyle(.secondary)
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
