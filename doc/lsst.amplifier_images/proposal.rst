
What problems does this attempt to solve?
-----------------------------------------

Running ``eotest`` pipelines
""""""""""""""""""""""""""""

The LSST Camera team wants to rewrite much of their ``eotest`` processing by using more DM code, but the DM code operates per-detector, and for various reasons ``eotest`` would prefer to work per-amplifier (and often in readout coordinates rather than physical coordinates).

DM's Gen3 middleware actually makes working per-amplifier harder, because Gen2 provided *some* support for single-amplifier raw loading and camera geometry.  These were not translated to Gen3 because it wasn't clear they were needed (they still don't seem to be needed, for *DM*) processing, and because in both cases they were built on rough foundations we didn't want to include in Gen3:

- The `lsst.afw.cameraGeom` classes were not intended to be used in a way that allowed multiple versions of the geometry (corresponding to different trim/assembly states or coordinate system conventions) for a single camera to be accessible.
  One major outcome of this is that amplifier geometry obtained directly from a `~lsst.afw.cameraGeom.Camera` object is not the same as what would be obtained from a ``raw`` image's attached `~lsst.afw.cameraGeom.Detector` object; this is just because they reflect different trim/flip states, but that is still different from all other instruments we support and a trap for the unwary.

- The Gen2 single-amplifier loading logic was built on top of Gen2's composite dataset system largely because other approaches were not viable.
  Gen3 solved those problems directly instead of via composites, but as a result its composition system was not designed to support this problem in the same way.


Solving `lsst.afw.cameraGeom` problems
""""""""""""""""""""""""""""""""""""""

Our camera geometry library includes three very different kinds of information:

- Amplifier-Detector geometry (overscan regions, orientation on the detector, etc.).
  This information is mostly static and exactly knowable (it's all integers), and when it isn't (e.g. tweaking overscan region sizes in the ``obs_lsst`` raw formatters), the corrections come from individual raw headers and image data, not a separate calibration product dataset.

- Amplifier parameters (gains, linearity, crosstalk, etc.).  This information neither static in time nor exactly knowable; we need to track our best measurements/models as calibration products.

- Detector-Camera geometry (optical distortions, detailed focal plane positions).
  This information is neither static (there are probably degrees of freedom that are slowly varying and per-exposure degrees of freedom) nor exactly knowable.  We need to track our best measurements/models as calibration products.

All of these need both an in-memory Python-object representation and an on-disk representation (as butler datasets and/or static git-controlled data).

Combining this information in the Python-object representation is often convenient for *consumers* of the information (one lookup gets you everything you might want), but combining it in the on-disk representation is problematic for *producers* of the information, because we don't want to rewrite things that weren't measured or merge different unrelated measurements (e.g. raw bias processing and astrometric fitting) just so we can write one latest-greatest-everything blob.
And of course making the Python-object representation wildly different from the on-disk representation complicates I/O.

Right now, `lsst.afw.cameraGeom.Camera` aggregates all of this information in both Python and on disk, so we're solving the problem of on-disk overaggregation by introducing new `lsst.ip.isr.IsrCalib` subclasses to provide an alternate, more producer-friendly containers for that "Amplifier parameter" information.
When we overhaul our approach to astrometry by switching from jointcal to GBDES, I think we'll need to do the same for the Detector-Camera geometry information.

All of that duplication with what's in `~lsst.afw.cameraGeom` is going to catch up with us, but maintenance of and changes to `~lsst.afw.cameraGeom` by the developers who use it most has been a constant problem, because it's a nontrivial C++ library and those developers are far more comfortable with Python.

Finally, we currently require a `~lsst.afw.cameraGeom.Camera` object just to load LSST raw images, because we assemble amplifiers (without trimming) on-the-fly behind the butler.
This is problematic because we'd like to eventually make that `~lsst.afw.cameraGeom.Camera` information time-dependent, and loadable only if a calibration collection is provided.
That's something no other butler dataset type demands, and something we'd really like to avoid supporting for just this case.
But this is also an operation that really only needs access to that mostly-static, exactly knowable Amplifier-Detector geometry subset.

Addressing all of these problems is well beyond the scope of this package, but as an alternate Python-object representation of just the Amplifier-Detector subset, I think it's a useful pilot project, and potentially a near-complete solution to at least the last problem.


What's in this package?
-----------------------

- An abstraction layer (``ImageSection``) that allows high-level objects to hold images (more precisely, ``lsst.afw.image.Image`` or ``lsst.afw.image.MaskedImage`` instances) or just the bounding boxes for images, allowing the higher-level objects in this package to have the same duality (e.g. you can have a `Amplifier` with just the bounding boxes for its data and overscan regions, or an `Amplifier` that has a full image with data and overscan region subimage views).

- Classes that represent amplifiers, explicitly distinguishing between `TrimmedAmplifier` and `UntrimmedAmplifier`.

- Classes that represent sets of amplifiers, again with the same trimmed vs. untrimmed distinction (`TrimmedAmplifierSet` and `UntrimmedAmplifierSet` base classes, respectively).
  Some of these are explicitly assembled (`AssembledTrimmedAmplifierSet` and `AssembledUntrimmedAmplifierSet`), with all amplifier images subimages of a complete detector image.  The unassembled amplifier sets (`UnassembledTrimmedamplifierSet` and `UnassembledUntrimmedAmplifierSet`) are designed to be usable with only some amplifiers present (e.g. only one).

This package does *not* contain gains, linearity, or other values that represent characterizations of amplifiers.
I'd much rather code get those from the `lsst.ip.isr.IsrCalib` subclasses and associated separate datasets that we're now adding.
If that's really onerous, I'm open to adding attributes here to hold some of that information (gains are probably the best candidate), as long as we're all on the same page about those ultimately being loaded as a calibration dataset by ISR (or other high-level code) and attached to these objects, rather than something that magically comes from reading a ``raw`` and that doing the (problematic) `~lsst.afw.cameraGeom.Camera` rendezvous behind the scenes.

How does this integrate with what we have?
------------------------------------------

Phase 1: Supporting ``eotest`` per-amplifier processing
"""""""""""""""""""""""""""""""""""""""""""""""""""""""

1. Add a ``raw.amps`` read-only component dataset type to the Gen3 Butler, returning an instance of an unspecified subclass of this package's ``AmplifierSet`` class.
   This would include an optional parameter to specifiy which amplifiers to load (default is all of them).
   For instruments like HSC that natively write raws as the assembled-but-untrimmed images use use for ``raw`` today, this would be an `AssembledUntrimmedAmplifierSet` when all amplifiers are requested.
   For instruments like the Rubin ones that natively write raws as per-amplifier HDUs (or instruments like HSC when only some amps are requested), this would be an `UnassembledUntrimmedAmplifierSet`.

2. Add similar ``.amps`` components to all appropriate master calibration datasets (at least biases, maybe others eventually if we like how that works).
   Some of these might return trimmed amplifier sets, of course, and all would be pre-assembled if all amplifiers are requested.

3. Reimplement reading ``raw`` to first load ``raw.amps``, then call `UntrimmedAmplifierSet.assembled_into_untrimmed` (a no-op for pre-assembled raws), then convert the `~lsst.afw.image.Image` into an `~lsst.afw.image.Exposure` with the right pixel type, and add `~lsst.afw.image.VisitInfo`, `~lsst.afw.geom.SkyWcs` and other components (note that `AmplifierSet` has an opaque `ObservationInfo` attribute we can use to the necessary information through.

4. Modify ISR to read ``raw.amps`` instead of ``raw``, but use the same function as in (3) to convert to `~lsst.afw.image.Exposure` when necessary; we can slowly push this point later in ISR by making more steps work on `AmplifierSet` objects instead.
   Ideally this would extend at least until we trim overscan regions, which would now just be a call to `AmplifierSet.assemble_into_trimmed`.
   Steps that are converted would naturally be directly usable for ``eotest`` use cases that want to run them on single-amplifier sets.

Phase 2: Hiding and starting to deprecate cameraGeom
""""""""""""""""""""""""""""""""""""""""""""""""""""

I've assumed that the first version of the ``raw.amps`` read implementation would still obtain a nominal camera from an `~lsst.obs.base.Instrument` class to populate the various bounding boxes.
Similarly, the "convert to `~lsst.afw.image.Exposure`" function used in the ``raw`` read implementation would need to extract a `lsst.afw.cameraGeom.Detector` object from that nominal camera as well, just to attach it to the `~lsst.afw.image.Exposure`.
The ISR invocation of that function could load the butler ``camera`` dataset and extract the detector object from that, however, and hence be totally ready for a time-varying camera (because that butler load would be like any other calibration product load).

There are two steps we can take next (in parallel, if effort is available):

- Reduce non-ISR usage of the ``raw`` dataset type in favor of ``raw.amps``, especially in code that uses ``raw.getDetector()`` just to get Amplifier-Detector geometry information.
  I suspect most such usage is in display utilities that also want access to *approximate* Detector-Camera geometry, but don't care about it at the level where variation in time matters.
  That's a problem with my "split up cameraGeom" proposal that needs solving; I don't think it's hard, but it's not something I've attempted here.

- Work on a way to build bounding-box-only `AmplifierSet` objects directly from (static!) ``obs_*_data`` state, like YAML files, then use this instead of a nominal `~lsst.afw.cameraGeom.Camera` from the `~lsst.obs.base.Instrument` class inside the ``raw.amps`` loader.

If both of those efforts are successful, we can start working on plans to deprecate the amplifier information in `lsst.afw.cameraGeom.Detector`, removing the duplication with both the `AmpliferSet` Amplifier-Detector geometry information and the `~lsst.ip.isr.IsrCalib` Amplifier parameter information.
And if we end up adding Detector-Camera geometry or Amplifier parameter information to `AmplifierSet` for convenience along the way, we'll still be in much better shape:

- We'll have broken the expectation that ``raw`` comes with *some* kinds of embedded calibration products (i.e. gains, linearity) that we currently have no way to populate correctly.
  (They will still come with Detector-Camera geometry information that suffers from that problem, but this is a good start.)

- We'll have moved the interfaces people actually use from C++ to Python.
