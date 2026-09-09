# py-eos
A Python wrapper for interfacing with Electronic Theatre Controls' Eos software over OSC.

Documentation on what you might be able to do via OSC can be found on the [Eos online manual](https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/23_Show_Control/08_OSC/OPEN_SOUND_CONTROL.htm?tocpath=Show%20Control%7COpen%20Sound%20Control%20(OSC)%7C_____0).

## Features
- TCP OSC connections
- Iterators for cues, groups, referenced data
- Default handlers for all standard emitted OSC events
- Keypresses and helpers for common actions

## Current State
`py-eos` is very much still in development. 
Most features exist because I had a plan on how to use them, and many features do not yet exist because I haven't needed to use them. 
Most development on this project is also suspiciously about three weeks before one of the shows that I'm designing for opens...
If you want to increase the development cadence, drop me a line about designing for your next show to make that period of frenzied development come sooner :wink:

If specific features are desired that do not exist yet, please submit a feature request and I can try to prioritize adding it!

## Installing and Usage
As `py-eos` is not in a finished state yet (or rather, presentable state), it is only available via GitHub. 
PyPi support will come when there are more unit tests and a semblance of polish has been added. 

Examples of how I've used this library can be found in the `examples/` directory. 

## Disclaimer
**Please backup your showfile before attempting to use this library!**
I use this on my own showfiles without disaster but you are using these tools at your own risk, knowing that OSC commands can totally destroy your showfile if used improperly. 
