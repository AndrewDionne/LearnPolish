import Foundation
import SwiftUI

// Parity implementation of V2's local expedition ledger: effort XP is
// personal/offline only, never a substitute for server-authoritative family XP.
struct PolandRegion: Decodable, Identifiable {
    let id: String
    let name: String
    let path: String
}

enum PolandRegionCatalog {
    static func load(bundle: Bundle = .main) throws -> [PolandRegion] {
        guard let url = bundle.url(forResource: "regions", withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.missing
        }
        let regions = try JSONDecoder().decode([PolandRegion].self, from: Data(contentsOf: url))
        guard regions.count == 16, Set(regions.map(\.id)).count == 16,
              regions.contains(where: { $0.id == "mazowieckie" }),
              regions.allSatisfy({ !$0.name.isEmpty && !$0.path.isEmpty }) else {
            throw CatalogLoadError.invalid("Source Poland regions changed")
        }
        return regions
    }
}

struct LocalXPEvent: Codable, Identifiable {
    let id: String
    let itemID: String
    let mode: PracticeMode
    let at: Date
    let xp: Int
    let baseXP: Int
    let expeditionXP: Int
    let tier: Int
    let regionID: String
}

struct LocalExpedition: Codable {
    var selectedRegion = "mazowieckie"
    var regionGoals: [String: Int] = [:]
    var events: [LocalXPEvent] = []

    private static let tierXP = [10, 14, 19, 26, 35]

    var totalXP: Int { events.reduce(0) { $0 + $1.xp } }
    var unlocked: Set<String> {
        Set(regionGoals.compactMap { id, goal in regionTotal(id) >= goal ? id : nil })
    }
    func regionTotal(_ id: String) -> Int {
        events.filter { $0.regionID == id }.reduce(0) { $0 + $1.expeditionXP }
    }
    func regionCost(_ id: String) -> Int {
        regionGoals[id] ?? nextCost
    }
    var nextCost: Int {
        Int((300 * pow(1 + 0.22 * Double(regionGoals.count), 1.35) / 10).rounded()) * 10
    }

    mutating func choose(_ id: String, validRegions: Set<String>) {
        guard validRegions.contains(id) else { return }
        selectedRegion = id
    }

    @discardableResult
    mutating func award(itemID: String, mode: PracticeMode, tier: Int, at: Date = Date()) -> LocalXPEvent? {
        guard (1...5).contains(tier), events.count < 20_000,
              !itemID.isEmpty, itemID.count < 181 else { return nil }
        let calendar = Calendar.current
        let date = calendar.dateComponents([.year, .month, .day], from: at)
        guard let year = date.year, let month = date.month, let day = date.day else { return nil }
        let dayKey = String(format: "%04d-%02d-%02d", year, month, day)
        let key = mode.rawValue + ":" + itemID + ":" + dayKey
        guard !events.contains(where: { $0.id == key }) else { return nil }
        let previous = events.filter { $0.itemID == itemID && $0.mode == mode }.count
        let base = Self.tierXP[tier - 1]
        let mapXP = previous == 0 ? base : (previous == 1 ? Int((Double(base) / 2).rounded()) : 0)
        if regionGoals[selectedRegion] == nil {
            regionGoals[selectedRegion] = nextCost
        }
        let event = LocalXPEvent(id: key, itemID: itemID, mode: mode,
                                 at: at, xp: base, baseXP: base,
                                 expeditionXP: mapXP, tier: tier,
                                 regionID: selectedRegion)
        events.append(event)
        return event
    }
}

/// The V2 source SVG uses only M, L and Z. We deliberately reject every
/// unsupported drawing token instead of silently changing region boundaries.
struct RegionOutline: Shape {
    let definition: String
    func path(in rect: CGRect) -> Path {
        let raw = definition.replacingOccurrences(of: "M", with: " M")
            .replacingOccurrences(of: "L", with: " L")
            .replacingOccurrences(of: "Z", with: " Z")
            .split(whereSeparator: { $0.isWhitespace }).map(String.init)
        let scale = min(rect.width / 585.0, rect.height / 555.0)
        let origin = CGPoint(x: (rect.width - 585.0 * scale) / 2,
                             y: (rect.height - 555.0 * scale) / 2)
        var path = Path()
        var index = 0
        while index < raw.count {
            let token = raw[index]
            if token == "Z" {
                path.closeSubpath()
                index += 1
                continue
            }
            guard (token.hasPrefix("M") || token.hasPrefix("L")),
                  raw.indices.contains(index + 1),
                  let x = Double(token.dropFirst()),
                  let y = Double(raw[index + 1]) else {
                return Path()
            }
            let point = CGPoint(x: origin.x + x * scale, y: origin.y + y * scale)
            if token.hasPrefix("M") { path.move(to: point) }
            else { path.addLine(to: point) }
            index += 2
        }
        return path
    }
}

struct PolandExpeditionView: View {
    @EnvironmentObject private var learner: LocalLearningStore
    private var expedition: LocalExpedition { learner.expedition }
    private var regions: [PolandRegion] { learner.regions }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading) {
                        Text("Your Poland expedition").font(.title2.bold())
                        Text("Earn personal XP through real practice.")
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    VStack(alignment: .trailing) {
                        Text("\(expedition.unlocked.count) / 16").font(.title2.bold())
                        Text("Unlocked").font(.caption).foregroundStyle(.secondary)
                    }
                }
                GeometryReader { proxy in
                    ZStack {
                        ForEach(regions) { region in
                            RegionOutline(definition: region.path)
                                .fill(expedition.unlocked.contains(region.id)
                                      ? Color.teal.opacity(0.65)
                                      : Color.gray.opacity(0.22))
                                .overlay {
                                    RegionOutline(definition: region.path)
                                        .stroke(expedition.selectedRegion == region.id
                                                ? Color.indigo : Color.secondary.opacity(0.5),
                                                lineWidth: expedition.selectedRegion == region.id ? 2.5 : 0.5)
                                }
                                .contentShape(RegionOutline(definition: region.path))
                                .onTapGesture { learner.chooseRegion(region.id) }
                                .accessibilityLabel(region.name)
                                .accessibilityAddTraits(.isButton)
                        }
                    }
                    .frame(width: proxy.size.width, height: proxy.size.height)
                }
                .aspectRatio(585.0 / 555.0, contentMode: .fit)

                if let chosen = regions.first(where: { $0.id == expedition.selectedRegion }) {
                    Text(chosen.name).font(.title3.bold())
                    let earned = expedition.regionTotal(chosen.id)
                    let goal = expedition.regionCost(chosen.id)
                    ProgressView(value: Double(min(earned, goal)), total: Double(goal))
                    Text("\(earned) / \(goal) XP")
                        .font(.subheadline.monospacedDigit())
                    if expedition.unlocked.contains(chosen.id) {
                        Label("Region unlocked", systemImage: "checkmark.circle")
                    }
                }
                Picker("Explore a region", selection: Binding(
                    get: { expedition.selectedRegion },
                    set: { learner.chooseRegion($0) }
                )) {
                    ForEach(regions) { region in
                        Text(region.name).tag(region.id)
                    }
                }
                .pickerStyle(.menu)
                Text("Every region is available to explore. This personal map stays on your device; family XP remains separate.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle("Expedition")
    }
}
