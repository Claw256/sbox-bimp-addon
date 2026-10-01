using System;
using Bimp;

/// <summary>
/// The addon's own code. It has to exist: an addon with no code compiles nothing, so its libraries (BIMP, in
/// Libraries/bimp) are never referenced or loaded, and the entities spawned without their components.
/// </summary>
internal static class BimpSandbox
{
	/// <summary> The components the entities' prefabs are made of - referenced so the library is linked. </summary>
	internal static readonly Type[] Components = { typeof( MediaPlayer ), typeof( MediaScreen ), typeof( MediaSpeaker ), typeof( MediaInteract ) };
}
