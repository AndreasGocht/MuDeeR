# MuDeer - A Mumble Bot using DeepSpeech for voice recognition

MuDeer is a Mumble Bot, which uses pymumble and DeepSpeech.
MuDeer relates either to "My Dear" or to "**MU**mble **DEE**pspeech **R**ecognition". However you whish :smile: .

You need to rename and adjust the `config.default.cfg` to `config.cfg`.

Moreover, to use voice recognition, you need voice models and scorers for DeepSpeech:
* English models can be found: https://github.com/mozilla/DeepSpeech/releases
* Other Languages: https://discourse.mozilla.org/t/links-to-pretrained-models/62688 

However, if you want to use a language other than German or English, you might want to do some localisation.
DeeR uses DeepSpeech HotWords to improve the prediction.
I recommend you to read https://phrase.com/blog/posts/translate-python-gnu-gettext/ to get an understanding of how localisation using gettext works.

Feel free to open an issue if you do have any questions ;-).  
