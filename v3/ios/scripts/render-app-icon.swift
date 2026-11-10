#!/usr/bin/env swift
import AppKit
import Foundation

// Deterministic, dependency-free macOS renderer for Brand/AppIcon.svg.
// The two paths/coordinates below mirror that checked-in, approved vector.
// Export opaque RGB: Xcode/App Store app icons cannot contain alpha or
// baked-in corner clipping. iOS applies the system rounded mask.
guard CommandLine.arguments.count == 2 else {
    fatalError("Usage: swift render-app-icon.swift OUTPUT.png")
}
let output = URL(fileURLWithPath: CommandLine.arguments[1])
let side = 1024
guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil,
                                     pixelsWide: side, pixelsHigh: side,
                                     bitsPerSample: 8, samplesPerPixel: 3,
                                     hasAlpha: false, isPlanar: false,
                                     colorSpaceName: .deviceRGB,
                                     bytesPerRow: 0, bitsPerPixel: 0),
      let graphics = NSGraphicsContext(bitmapImageRep: bitmap) else {
    fatalError("Cannot allocate opaque RGB bitmap")
}
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = graphics
let context = graphics.cgContext
context.setAllowsAntialiasing(true)
context.setShouldAntialias(true)
context.setFillColor(NSColor.white.cgColor)
context.fill(CGRect(x: 0, y: 0, width: side, height: side))

// Convert SVG's upper-left origin to Quartz's lower-left origin.
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
context.setFillColor(NSColor(srgbRed: 16.0 / 255, green: 35.0 / 255,
                             blue: 51.0 / 255, alpha: 1).cgColor)
context.drawPath(using: .eoFill)
context.restoreGState()

context.setFillColor(NSColor(srgbRed: 86.0 / 255, green: 207.0 / 255,
                             blue: 174.0 / 255, alpha: 1).cgColor)
context.fillEllipse(in: CGRect(x: 855.6, y: 731.5, width: 94, height: 94))
graphics.flushGraphics()
NSGraphicsContext.restoreGraphicsState()
guard let png = bitmap.representation(using: .png, properties: [:]) else {
    fatalError("RGB PNG export failed")
}
try FileManager.default.createDirectory(
    at: output.deletingLastPathComponent(), withIntermediateDirectories: true)
try png.write(to: output, options: .atomic)
print("Prepared square, opaque Path to Polish iPhone icon: \(output.path)")
