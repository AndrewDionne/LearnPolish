import SwiftUI

/// Tab changes and lesson launches belong to a single application-level
/// navigation coordinator. A Library selection starts work in Practice;
/// Library itself never hosts an exercise screen.
enum LearningTab: Hashable {
    case home, library, practice, expedition, progress
}

enum PracticeRoute: Hashable {
    case lesson(String)
    case guided(String)
    case soundLab
    case scenarios
}

@MainActor final class LearningNavigation: ObservableObject {
    @Published var tab: LearningTab = .home
    @Published var practicePath: [PracticeRoute] = []

    func openPractice(_ route: PracticeRoute) {
        // Starting another set doesn't delete saved positions. The Practice
        // root remains accessible with a Back action and the tab persists.
        if practicePath.last != route {
            practicePath = [route]
        }
        tab = .practice
    }

    func showPractice() {
        tab = .practice
    }
}
