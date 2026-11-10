#!/usr/bin/env swift
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

// Deterministic, dependency-free macOS renderer for Brand/AppIcon.svg.
// This shape mirrors the checked-in approved vector. Its full white square
// has no clipping, rounded corners or transparency: iOS applies its mask.
guard CommandLine.arguments.count == 2 else {
    fatalError("Usage: swift render-app-icon.swift OUTPUT.png")
}
let output = URL(fileURLWithPath: CommandLine.arguments[1])
let side = 1024
let colorSpace = CGColorSpaceCreateDeviceRGB()
// Four aligned bytes per pixel, with the fourth explicitly *unused*;
// Quartz bitmap contexts cannot reliably allocate 24-bit RGB pixels.
guard let context = CGContext(data: nil, width: side, height: side,
                              bitsPerComponent: 8, bytesPerRow: side * 4,
                              space: colorSpace,
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else {
    fatalError("Cannot allocate opaque RGB bitmap context")
}
context.setAllowsAntialiasing(true)
context.setShouldAntialias(true)
context.setFillColor(CGColor(srgbRed: 1, green: 1, blue: 1, alpha: 1))
context.fill(CGRect(x: 0, y: 0, width: side, height: side))

// Convert upper-left SVG coordinates to Quartz's lower-left origin.
context.translateBy(x: 0, y: CGFloat(side))
context.scaleBy(x: 1, y: -1)
context.saveGState()
context.translateBy(x: 12, y: 138)
context.scaleBy(x: 1.46, y: 1.22)
let mark = CGMutablePath()
mark.move(to: CGPoint(x: 126, y: 67))
mark.addLine(to: CGPoint(x: 305, y: 67))
mark.addCurve(to: CGPoint(x: 507, y: 212),
              control1: CGPoint(x: 438, y: 67), control2: CGPoint(x: 507, y: 120))
mark.addCurve(to: CGPoint(x: 305, y: 352),
              control1: CGPoint(x: 507, y: 310), control2: CGPoint(x: 438, y: 352))
mark.addLine(to: CGPoint(x: 192, y: 352))
mark.addLine(to: CGPoint(x: 192, y: 502))
mark.addLine(to: CGPoint(x: 560, y: 502))
mark.addLine(to: CGPoint(x: 560, y: 560))
mark.addLine(to: CGPoint(x: 126, y: 560))
mark.addLine(to: CGPoint(x: 126, y: 352))
mark.addLine(to: CGPoint(x: 60, y: 352))
mark.addLine(to: CGPoint(x: 60, y: 291))
mark.addLine(to: CGPoint(x: 126, y: 291))
mark.closeSubpath()
mark.move(to: CGPoint(x: 192, y: 125))
mark.addLine(to: CGPoint(x: 192, y: 292))
mark.addLine(to: CGPoint(x: 303, y: 292))
mark.addCurve(to: CGPoint(x: 440, y: 213),
              control1: CGPoint(x: 397, y: 292), control2: CGPoint(x: 440, y: 266))
mark.addCurve(to: CGPoint(x: 303, y: 125),
              control1: CGPoint(x: 440, y: 156), control2: CGPoint(x: 397, y: 125))
mark.closeSubpath()
context.addPath(mark)
context.setFillColor(CGColor(srgbRed: 16.0 / 255, green: 35.0 / 255,
                             blue: 51.0 / 255, alpha: 1))
context.drawPath(using: .eoFill)
context.restoreGState()

context.setFillColor(CGColor(srgbRed: 86.0 / 255, green: 207.0 / 255,
                             blue: 174.0 / 255, alpha: 1))
context.fillEllipse(in: CGRect(x: 855.6, y: 731.5, width: 94, height: 94))
guard let image = context.makeImage() else { fatalError("Bitmap image unavailable") }
try FileManager.default.createDirectory(
    at: output.deletingLastPathComponent(), withIntermediateDirectories: true)
guard let destination = CGImageDestinationCreateWithURL(
        output as CFURL, UTType.png.identifier as CFString, 1, nil) else {
    fatalError("Unable to create PNG destination")
}
CGImageDestinationAddImage(destination, image, nil)
guard CGImageDestinationFinalize(destination) else { fatalError("PNG export failed") }
print("Prepared square opaque Path to Polish iPhone icon: \(output.path)")
