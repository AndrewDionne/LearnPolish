import SwiftUI
import UniformTypeIdentifiers

struct AppShell: View {
    @StateObject private var navigation = LearningNavigation()

    var body: some View {
        TabView(selection: $navigation.tab) {
            NavigationStack { HomeScreen() }
                .tabItem { Label("Home", systemImage: "house") }
                .tag(LearningTab.home)
            NavigationStack { LibraryScreen() }
                .tabItem { Label("Library", systemImage: "books.vertical") }
                .tag(LearningTab.library)
            NavigationStack(path: $navigation.practicePath) {
                ReviewScreen()
                    .navigationDestination(for: PracticeRoute.self) { route in
                        PracticeDestinationScreen(route: route)
                    }
            }
            .tabItem { Label("Practice", systemImage: "rectangle.stack") }
            .tag(LearningTab.practice)
            NavigationStack { PolandExpeditionView() }
                .tabItem { Label("Expedition", systemImage: "map") }
                .tag(LearningTab.expedition)
            NavigationStack { ProgressScreen() }
                .tabItem { Label("Progress", systemImage: "chart.bar") }
                .tag(LearningTab.progress)
        }
        .environmentObject(navigation)
        .tint(.indigo)
    }
}

struct PracticeDestinationScreen: View {
    let route: PracticeRoute
    @EnvironmentObject private var learner: LocalLearningStore

    var body: some View {
        switch route {
        case .lesson(let id):
            if let lesson = learner.lessons.first(where: { $0.id == id }) {
                LessonScreen(lesson: lesson)
            } else {
                ContentUnavailableView("Lesson unavailable", systemImage: "exclamationmark.triangle")
            }
        case .guided(let id):
            if let step = learner.guidedFoundations.first(where: { $0.id == id }) {
                GuidedPracticeScreen(step: step)
            } else {
                ContentUnavailableView("Lesson unavailable", systemImage: "exclamationmark.triangle")
            }
        case .soundLab:
            SoundStudioScreen()
        case .scenarios:
            TouristUnitsScreen()
        }
    }
}

struct HomeScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var family: NativeFamilySession
    @EnvironmentObject private var navigation: LearningNavigation

    private var latestActivity: Date? {
        learner.profile.records.values.compactMap(\.lastAttempt).max()
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Path to Polish")
                    .font(.largeTitle.bold())
                Text("Your learning today")
                    .foregroundStyle(.secondary)
                #if DEBUG
                NavigationLink {
                    NativeAudioChannelProbeScreen()
                } label: {
                    Label("Audio check · test headphones", systemImage: "headphones")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.bordered)
                .accessibilityIdentifier("debug.audio.channel-check")
                #endif

                if let message = learner.catalogError {
                    ContentUnavailableView("Lessons unavailable",
                                           systemImage: "exclamationmark.triangle",
                                           description: Text(message))
                } else {
                    HStack(spacing: 12) {
                        homeMetric("\(learner.expedition.totalXP)", "Personal XP",
                                   icon: "star")
                        homeMetric("\(learner.completedItems)", "Items practised",
                                   icon: "checkmark.circle")
                    }
                    HStack(spacing: 12) {
                        homeMetric("\(learner.dueReviews.count)", "Reviews due",
                                   icon: "arrow.clockwise")
                        homeMetric("\(learner.activeGuidedSteps.count + learner.activePracticeLessons.count)",
                                   "Started sets", icon: "bookmark")
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Continue your journey").font(.headline)
                        if let route = learner.homeLearningRoute {
                            switch route {
                            case .guided(let step):
                                Text(step.title).font(.title2.weight(.semibold))
                                Text(step.stage).foregroundStyle(.secondary)
                                Button {
                                    navigation.openPractice(.guided(step.id))
                                } label: {
                                    Label("Continue in Practice", systemImage: "arrow.right")
                                        .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(.borderedProminent)
                            case .core(let lesson):
                                Text(lesson.title).font(.title2.weight(.semibold))
                                Text("Your next original course lesson").foregroundStyle(.secondary)
                                Button {
                                    navigation.openPractice(.lesson(lesson.id))
                                } label: {
                                    Label("Continue in Practice", systemImage: "arrow.right")
                                        .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(.borderedProminent)
                            }
                        } else {
                            Text("Open Practice to begin a lesson.")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.quaternary.opacity(0.4),
                                in: RoundedRectangle(cornerRadius: 18))

                    HStack {
                        VStack(alignment: .leading, spacing: 5) {
                            Text("Recent activity").font(.headline)
                            if let latestActivity {
                                Text("Last practice · " + latestActivity.formatted(
                                    date: .abbreviated, time: .shortened))
                                    .font(.subheadline).foregroundStyle(.secondary)
                            } else {
                                Text("Your first practice will appear here.")
                                    .font(.subheadline).foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        Button("Practice") { navigation.showPractice() }
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Family progress").font(.headline)
                        if family.isConnected {
                            Text("\(family.groups.count) connected family group(s)")
                                .foregroundStyle(.secondary)
                            Text("Family scores are provided by your connected group, not estimated from local XP.")
                                .font(.footnote).foregroundStyle(.secondary)
                        } else {
                            Text("Not connected · your learning stays private")
                                .foregroundStyle(.secondary)
                        }
                        NavigationLink {
                            NativeFamilyAccountScreen()
                        } label: {
                            Label(family.isConnected ? "View team progress" : "Optional family connection",
                                  systemImage: "person.2")
                        }
                    }
                    .padding(16)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.quaternary.opacity(0.25),
                                in: RoundedRectangle(cornerRadius: 16))
                }
                if let error = learner.saveError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.footnote).foregroundStyle(.red)
                }
            }
            .padding()
        }
        .navigationTitle("Home")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func homeMetric(_ value: String, _ label: String,
                            icon: String) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Image(systemName: icon).foregroundStyle(.indigo)
            Text(value).font(.title2.bold()).monospacedDigit()
            Text(label).font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(15)
        .background(.quaternary.opacity(0.25),
                    in: RoundedRectangle(cornerRadius: 14))
    }
}

struct LibraryScreen: View {
    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var navigation: LearningNavigation
    @State private var query = ""

    private var journeys: [NativeJourneyCollection] {
        NativeJourneyCatalog.collections(
            course: learner.course,
            placements: learner.coreJourney?.placements ?? [:])
    }

    private func matches(_ lesson: Lesson) -> Bool {
        query.isEmpty || lesson.title.localizedCaseInsensitiveContains(query) ||
            (lesson.description?.localizedCaseInsensitiveContains(query) ?? false)
    }

    var body: some View {
        List {
            if let error = learner.catalogError {
                Section { Text(error).foregroundStyle(.red) }
            }
            Section("Start here") {
                NavigationLink {
                    GuidedFoundationsScreen()
                } label: {
                    Label("First words and basic grammar",
                          systemImage: "text.book.closed")
                }
            }
            Section("Learning journeys") {
                ForEach(journeys) { journey in
                    if query.isEmpty ||
                        journey.title.localizedCaseInsensitiveContains(query) ||
                        journey.lessons.contains(where: matches) {
                        NavigationLink {
                            JourneyCollectionScreen(collection: journey)
                        } label: {
                            let progress = NativeJourneyCatalog.snapshot(
                                journey, records: learner.profile.records)
                            VStack(alignment: .leading, spacing: 7) {
                                Text(journey.title).font(.headline)
                                Text("\(journey.lessons.count) lessons · \(progress.practisedLessons) practised")
                                    .font(.subheadline).foregroundStyle(.secondary)
                                ProgressView(value: Double(progress.practisedLessons),
                                             total: Double(max(1, progress.totalLessons)))
                                HStack {
                                    Text("\(progress.startedLessons) started")
                                    Spacer()
                                    Text(progress.recallPercentage.map {
                                        "Recall accuracy \($0)%"
                                    } ?? "Recall not assessed")
                                }
                                .font(.caption).foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
            Section("Extras") {
                Button {
                    navigation.openPractice(.soundLab)
                } label: {
                    Label("Alphabet and Sound Lab", systemImage: "waveform")
                }
                Button {
                    navigation.openPractice(.scenarios)
                } label: {
                    Label("Everyday scenarios", systemImage: "figure.walk")
                }
                ForEach(learner.explore.filter(matches)) { lesson in
                    Button {
                        navigation.openPractice(.lesson(lesson.id))
                    } label: {
                        LessonRow(lesson: lesson)
                    }
                }
            }
        }
        .searchable(text: $query, prompt: "Find a journey or lesson")
        .navigationTitle("Library")
    }
}

struct JourneyCollectionScreen: View {
    let collection: NativeJourneyCollection
    @EnvironmentObject private var learner: LocalLearningStore
    @EnvironmentObject private var navigation: LearningNavigation

    var body: some View {
        List {
            Section {
                let progress = NativeJourneyCatalog.snapshot(
                    collection, records: learner.profile.records)
                LabeledContent("Lessons practised",
                               value: "\(progress.practisedLessons) / \(progress.totalLessons)")
                if let score = progress.recallPercentage {
                    LabeledContent("Recall accuracy", value: "\(score)%")
                } else {
                    Text("Recall not assessed yet")
                        .foregroundStyle(.secondary)
                }
            }
            Section("Lessons") {
                ForEach(collection.lessons) { lesson in
                    Button {
                        navigation.openPractice(.lesson(lesson.id))
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            LessonRow(lesson: lesson)
                            let count = lesson.items.filter { item in
                                PracticeMode.allCases.contains { mode in
                                    (learner.profile.records[mode.rawValue + ":" + item.id]?.attempts ?? 0) > 0
                                }
                            }.count
                            Text("\(count) / \(lesson.items.count) items practised")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .navigationTitle(collection.title)
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
            if let error = learner.catalogError {
                Section { Text(error).foregroundStyle(.red) }
            }
            Section("Your active learning sets") {
                if learner.activeGuidedSteps.isEmpty && learner.activePracticeLessons.isEmpty {
                    Text("Choose a lesson in Library to begin. You can pause and return to several sets.")
                        .foregroundStyle(.secondary)
                }
                ForEach(learner.activeGuidedSteps) { step in
                    NavigationLink(value: PracticeRoute.guided(step.id)) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(step.title).font(.headline)
                            Text("\(learner.guidedPractisedCount(step)) of \(step.items.count) phrases practised")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                ForEach(learner.activePracticeLessons) { lesson in
                    NavigationLink(value: PracticeRoute.lesson(lesson.id)) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(lesson.title).font(.headline)
                            let tried = lesson.items.filter { item in
                                PracticeMode.allCases.contains { mode in
                                    (learner.profile.records[mode.rawValue + ":" + item.id]?.attempts ?? 0) > 0
                                }
                            }.count
                            Text("\(tried) of \(lesson.items.count) items practised")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            if !dueGroups.isEmpty {
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
                Section("Scheduled review") {
                    ForEach(dueGroups) { group in
                        NavigationLink {
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
            } else {
                Section {
                    Text("Nothing due yet. New reviews appear after real learning attempts.")
                        .foregroundStyle(.secondary)
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
