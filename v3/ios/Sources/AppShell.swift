import SwiftUI
import UniformTypeIdentifiers

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
                    if let route = learner.homeLearningRoute {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Continue learning")
                                .font(.headline)
                            switch route {
                            case .guided(let guided):
                                Text(guided.title)
                                    .font(.title2.weight(.semibold))
                                Text(guided.stage)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            case .core(let lesson):
                                Text(lesson.title)
                                    .font(.title2.weight(.semibold))
                                if let description = lesson.description {
                                    Text(description).foregroundStyle(.secondary)
                                }
                            }
                            NavigationLink {
                                switch route {
                                case .guided(let guided):
                                    GuidedPracticeScreen(step: guided)
                                case .core(let lesson):
                                    LessonScreen(lesson: lesson, resumeAtNextUnseen: true)
                                }
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

                    if !learner.dueReviews.isEmpty {
                        NavigationLink {
                            NativeDailyReviewSessionScreen(cards:
                                NativeDailyReviewQueue.snapshot(
                                    lessons: learner.lessons,
                                    records: learner.profile.records, now: Date()))
                        } label: {
                            Label("Review \(min(learner.dueReviews.count, NativeDailyReviewQueue.batchLimit)) due",
                                  systemImage: "rectangle.stack")
                        }
                        .font(.headline)
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
                    #if DEBUG
                    NavigationLink {
                        NativeAudioChannelProbeScreen()
                    } label: {
                        Label("Audio check (developer build)", systemImage: "headphones")
                    }
                    .font(.footnote)
                    #endif
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
                Section {
                    NavigationLink {
                        NativeDailyReviewSessionScreen(cards:
                            NativeDailyReviewQueue.snapshot(
                                lessons: learner.lessons,
                                records: learner.profile.records, now: Date()))
                    } label: {
                        Label("Review up to \(min(learner.dueReviews.count, NativeDailyReviewQueue.batchLimit)) due",
                              systemImage: "rectangle.stack.fill")
                    }
                }
                Section("Scheduled review by lesson") {
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
    @State private var showExporter = false
    @State private var exportDocument: LocalProgressArchiveDocument?
    @State private var confirmLocalErase = false
    @State private var confirmDeleteBackups = false
    @State private var showImporter = false
    @State private var combineLinkedImport = false
    @State private var pendingRestore: LocalRestorePreview?
    @State private var pendingLinkedMerge: NativeLinkedDevicePreview?
    @State private var storageMessage: String?

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
                Text("Progress is saved privately on this device. CloudKit backup and automatic family sharing are not enabled.")
                    .foregroundStyle(.secondary)
                Button {
                    do {
                        exportDocument = try learner.makeLocalExport()
                        storageMessage = nil
                        showExporter = true
                    } catch {
                        storageMessage = error.localizedDescription
                    }
                } label: {
                    Label("Export local progress", systemImage: "square.and.arrow.up")
                }
                Text("The exported JSON contains your local learning record and history, not your password, microphone recordings or family account. Keep the file private.")
                    .font(.footnote).foregroundStyle(.secondary)
                Button {
                    storageMessage = nil
                    combineLinkedImport = false
                    showImporter = true
                } label: {
                    Label("Restore progress from a file", systemImage: "square.and.arrow.down")
                }
                Button {
                    storageMessage = nil
                    combineLinkedImport = true
                    showImporter = true
                } label: {
                    Label("Combine linked-device progress", systemImage: "arrow.triangle.merge")
                }
                Text("To link a second iPhone, first explicitly Restore a copy of this learner's exported file there. After each phone has practised, exchange an export and choose Combine. Different anonymous learners cannot be combined.")
                    .font(.footnote).foregroundStyle(.secondary)
                if !learner.localRestoreBackups.isEmpty {
                    ForEach(Array(learner.localRestoreBackups.prefix(5))) { backup in
                        Button {
                            do {
                                pendingRestore = try learner.previewLocalBackup(backup)
                                storageMessage = nil
                            } catch {
                                storageMessage = error.localizedDescription
                            }
                        } label: {
                            Label("Earlier backup · " + backup.savedAt.formatted(
                                date: .abbreviated, time: .shortened),
                                systemImage: "clock.arrow.circlepath")
                        }
                    }
                }
                Text("Restore replaces local progress, while Combine merges only two verified copies of the same explicitly transferred learner. Both require confirmation and first save a recoverable local backup; neither connects an account or iCloud.")
                    .font(.footnote).foregroundStyle(.secondary)
                    .font(.footnote).foregroundStyle(.secondary)
                if !learner.localRestoreBackups.isEmpty {
                    Button(role: .destructive) {
                        confirmDeleteBackups = true
                    } label: {
                        Label("Delete saved restore backups", systemImage: "trash.slash")
                    }
                }
                Button(role: .destructive) {
                    confirmLocalErase = true
                } label: {
                    Label("Erase local learning progress", systemImage: "trash")
                }
                if let error = learner.saveError {
                    Text(error).foregroundStyle(.red)
                }
                if let storageMessage {
                    Text(storageMessage).font(.footnote).foregroundStyle(.secondary)
                }
            }
            Section("Optional family") {
                NavigationLink {
                    NativeFamilyAccountScreen()
                } label: {
                    Label("Family connection and weekly scores", systemImage: "person.2")
                }
                Text("An account is not needed to learn. Family connection is voluntary; personal progress stays on this iPhone.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("My progress")
        .fileExporter(isPresented: $showExporter, document: exportDocument,
                      contentType: .json, defaultFilename: "PathToPolish-Progress") { result in
            switch result {
            case .success:
                storageMessage = "Export saved to the location you selected."
            case .failure(let error):
                storageMessage = "Export could not be saved: " + error.localizedDescription
            }
            exportDocument = nil
        }
        .fileImporter(isPresented: $showImporter, allowedContentTypes: [.json],
                      allowsMultipleSelection: false) { result in
            do {
                let files = try result.get()
                guard let file = files.first else {
                    throw LocalProgressArchiveError.invalid
                }
                if combineLinkedImport {
                    pendingLinkedMerge = try learner.previewLinkedDeviceMerge(from: file)
                } else {
                    pendingRestore = try learner.previewImportedProgress(from: file)
                }
                storageMessage = nil
            } catch {
                storageMessage = error.localizedDescription
            }
        }
        .sheet(item: $pendingRestore) { candidate in
            LocalRestoreReviewSheet(candidate: candidate,
                currentAttempts: learner.attempts,
                currentXP: learner.expedition.totalXP) {
                    let backup = try learner.restoreLocalProgress(candidate)
                    storageMessage = "Progress restored. Previous progress saved to a local backup."
                    return backup
                }
        }
        .sheet(item: $pendingLinkedMerge) { candidate in
            NativeLinkedMergeReviewSheet(review: candidate,
                currentXP: learner.expedition.totalXP) {
                    let backup = try learner.applyLinkedDeviceMerge(candidate)
                    storageMessage = "Linked-device history combined. Your earlier on-device progress is preserved as a private restore backup."
                    return backup
                }
        }
        .alert("Erase learning progress from this iPhone?",
               isPresented: $confirmLocalErase) {
            Button("Erase local progress", role: .destructive) {
                if learner.resetLocalProgress() {
                    storageMessage = "Local learning progress was erased on this iPhone."
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This clears the active local learning profile. Previously saved restore backups remain recoverable until you delete them separately. Exported files and family-server records are not affected.")
        }
        .confirmationDialog("Delete saved local restore backups?",
            isPresented: $confirmDeleteBackups, titleVisibility: .visible) {
            Button("Delete restore backups", role: .destructive) {
                do {
                    let count = try learner.deleteLocalRestoreBackups()
                    storageMessage = "\(count) local restore backup(s) deleted. Current progress and exported files were not changed."
                } catch {
                    storageMessage = "Some backups could not be deleted: " + error.localizedDescription
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("These private recovery copies will not be recoverable after deletion. This does not erase your current learner profile or exports stored outside the app.")
        }
    }
}
