import SwiftUI

/// Family map shows server-authoritative regional progress only.
/// It never imports local expedition XP or starts a background upload.
struct NativeFamilyGroupMap: View {
    let sourceRegions: [PolandRegion]
    let contributions: [NativeFamilySummary.Region]
    @State private var selectedRegion: String?

    private var selected: PolandRegion? {
        if let selectedRegion,
           let match = sourceRegions.first(where: { $0.id == selectedRegion }) {
            return match
        }
        return sourceRegions.first(where: { region in
            contributions.contains(where: { $0.region == region.id })
        }) ?? sourceRegions.first
    }

    private func progress(for id: String) -> NativeFamilySummary.Region? {
        contributions.first { $0.region == id }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            GeometryReader { proxy in
                ZStack {
                    ForEach(sourceRegions) { region in
                        RegionOutline(definition: region.path)
                            .fill(color(for: region))
                            .overlay {
                                RegionOutline(definition: region.path)
                                    .stroke(
                                        selected?.id == region.id ? Color.indigo
                                            : Color.secondary.opacity(0.4),
                                        lineWidth: selected?.id == region.id ? 2 : 0.5
                                    )
                            }
                            .contentShape(RegionOutline(definition: region.path))
                            .onTapGesture { selectedRegion = region.id }
                            .accessibilityLabel(region.name)
                            .accessibilityAddTraits(.isButton)
                    }
                }
                .frame(width: proxy.size.width, height: proxy.size.height)
            }
            .aspectRatio(585.0 / 555.0, contentMode: .fit)

            if let selected {
                Text(selected.name).font(.headline)
                if let region = progress(for: selected.id) {
                    ProgressView(value: Double(min(region.earned, region.target)),
                                 total: Double(region.target))
                    Text("\(region.earned) / \(region.target) group XP")
                        .font(.subheadline.monospacedDigit())
                    if region.unlocked {
                        Label("Unlocked by the group", systemImage: "checkmark.circle")
                            .font(.subheadline)
                    }
                } else {
                    Text("No group progress recorded in this region")
                        .foregroundStyle(.secondary).font(.subheadline)
                }
            }
            Text("Group progress comes from the private family service. Your personal offline expedition remains separate.")
                .font(.footnote).foregroundStyle(.secondary)
        }
    }

    private func color(for region: PolandRegion) -> Color {
        guard let entry = progress(for: region.id) else { return .gray.opacity(0.2) }
        if entry.unlocked { return .teal.opacity(0.65) }
        return .indigo.opacity(0.22)
    }
}
