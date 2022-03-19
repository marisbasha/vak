(howto-user-spect)=

# How do I use my own spectrograms?

`vak` has built-in functionality to generate spectrograms
from audio files. It will do this when you build a dataset
with the `vak prep` command, and specify an `audio_format`
in your configuration file.

But you can also use spectrograms that you generate with your own code,
taking advantage of existing libraries in the scientific Python ecosystem,
such as [librosa](https://librosa.org/doc/main/index.html).

There are two formats you can use for your own spectrograms,
either `.npz` or `.mat` files.
`.npz` is a `numpy` library format,
for a file that can contain multiple arrays.
The `.mat` extension denotes
the equivalent Matlab data file format; many labs
have existing codebases that generate spectrograms using Matlab.
You will specify either `npz` or `vak` in the `[PREP]` section
of your `.toml` configuration file.

## Step-by-step

This recipe describes how to using spectrograms generated with Python code.
For Matlab code, the only difference is, you would save each spectrogram in a `.mat` file,
using the built-in `save` function.

1. Write your script that generates spectrograms for each of your audio files,
   e.g. using [librosa](https://librosa.org/doc/main/index.html).

2. In that script, save each spectrogram in an `.npz` file,
   along with the vectors of times and frequencies that are typically
   returned by a function that computes spectrograms.

   The naming and the contents of the file should match the specification in {ref}`spect_file_format`.

   - It should contain a spectrogram array `s`, the vector of time bins `t`,
     the vector of frequency bins `f`, and the path to the audio file the spectrogram was
     generated from, `audio_path`.
   - It should be named the same as the audio file, but with the array file format extension added,
     e.g., a spectrogram file generated from `zb1_20211220_0714.wav` should be named `zb1_20211220_0714.wav.npz`

3. In the `[PREP]` section of your `vak` configuration file,
   specify:

   `spect_format = 'npz'`

   For the `data_dir` option,
   put the path to the directory that contains all `npz` files saved by your script.

4. Run `vak prep` with that configuration file.
   `vak` will look for `npz` files in the `data_dir` directory,
   and link them to the correct annotation by removing the `npz` from the file name
   to recover the name of the audio file, and then finding an annotation
   for that audio file.