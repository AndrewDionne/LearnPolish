import SwiftUI

@main
struct PathToPolishApp: App {
    @StateObject private var learner = LocalLearningStore()

    var body: some Scene {
        WindowGroup {
            AppShell()
                .environmentObject(learner)
        }
    }
}
