"""Corrections for exported callout anchors that miss the part they name.

(slug, view) -> {anchor name: (dx, dy)} in the exported drawing's own units (scaled with the view).
Keep each entry to the smallest move that lands the dot on the part, and say why in a comment.
"""
SHIFTS = {
    ('quiet-stair','A'):{'VERTICAL CARRIAGES':(-39,-1)},  # c038: the front-left carriage's screw, nearest its label, not the second carriage deep in the frame
    ('seam-surgeon','A'):{'INSPECTION ARRAY':(-8,3)},  # c065: onto the inspection bogie's visible face below the pipe; the array itself sits behind the pipe in A
    ('sleep-cocoon','A'):{'RESTING WORKER':(3,29),'FOOT PLATFORM':(-34,-4)},  # c099: the chest, not beside the eye; the platform's near edge by its label
    ('reef-nursery','A'):{'SEABED ANCHOR':(-107,-64),'DAVIT':(1,39)},  # b02: the free far-left anchor block, not one behind a lattice tree; the davit post just above its winch, level with the label
    ('sun-still','A'):{'HELIOSTAT':(120,15)},  # b03: the right-hand front mirror, not the product-shed roof
    ('manta-foil','A'):{'RETRACTABLE FOILS':(6,26)},  # c006: the front hinged strut, not the hull side above it
    ('memory-kiln','A'):{'FOCUS OBJECTIVE':(-7,26)},  # c017: the objective's lower mount ring, so the leader passes under the pulse source
    ('fibre-braid','A'):{'MANDREL CHUCK':(-19,12)},  # c025: the chuck face inside the carrier ring, not a bobbin in front of it
    ('petal-eye','A'):{'SUN SHADE':(-3,-20)},  # c031: a sunshade petal, not the flat radiator panel
    ('light-sail','A'):{'MEMBRANE':(-158,-61)},  # c001: the left quadrant's film, so with CARGO SPINE gone MEMBRANE takes the left column and SAIL ROOT's leader stays off the hub
    ('key-concord','A'):{'WITHDRAWAL':(-11.5,-4.3)},  # c104: onto the knurled crown's rim, from the bolt end behind it; the leader then clears key two's bow
    ('volumetric-stage','A'):{'CLOCK DISTRIBUTION':(15,-11)},  # o12: onto the timing controller's front face, out of the truss clutter where the dot was lost
}
