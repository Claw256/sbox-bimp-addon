using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Editor.Mcp;
using Sandbox;

namespace Editor;

/// <summary>
/// Publishes the addon's entities without clicking through the UI - the same steps as the editor's Batch Publisher
/// (<c>ProjectPublisher.FromAsset</c>, <c>PrePublish</c>, <c>UploadFiles</c>, <c>Publish</c>). An MCP tool, so it can be
/// run from an agent connected to the editor. Editor only: this code isn't part of the published entities.
/// </summary>
[McpToolset( "bimp_sandbox", "Publishing the BIMP for Sandbox entities (Media Screen, Media Speaker)" )]
public static class PublishEntities
{
	static readonly (string Path, bool BundleCode)[] Entities =
	{
		("entities/media_screen.sent", true),
		("entities/media_speaker.sent", false),
	};

	/// <summary>
	/// List what each BIMP entity (Media Screen, Media Speaker) would upload to sbox.game, and with publish = true,
	/// upload and publish a new revision of each. Returns a report per entity: its package ident, type, files and errors.
	/// </summary>
	[McpTool( "bimp_publish_entities" )]
	public static async Task<string> Run( [System.ComponentModel.Description( "Actually upload and publish. False only lists what would be uploaded." )] bool publish = false )
	{
		var report = new StringBuilder();

		foreach ( var (path, bundleCode) in Entities )
		{
			var asset = AssetSystem.FindByPath( path );
			if ( asset is null )
			{
				report.AppendLine( $"{path}: not found" );
				continue;
			}

			var settings = asset.Publishing;
			if ( !settings.Enabled || settings.ProjectConfig.Org == "local" )
			{
				report.AppendLine( $"{path}: publishing isn't enabled for an organisation (org '{settings.ProjectConfig.Org}')" );
				continue;
			}

			try
			{
				var upload = await ProjectPublisher.FromAsset( asset );
				if ( upload is null )
				{
					report.AppendLine( $"{path}: the asset can't be published" );
					continue;
				}

				// media_screen.sent carries the compiled code and media_speaker.sent references rexi.bimp_screen
				// so BIMP is loaded once and always ships the latest code on sbox.game ("Type": "addon" projects
				// publish only to Steam Workshop). Note: ResourcePublishContext.IncludeCode was obsoleted to
				// always return false, and Project.CanPublishCode() only allows "game"/"library", so we pass a
				// temporary "game" type to EditorUtility.Projects.Compile while keeping the published package "sent".
				var references = settings.ProjectConfig.PackageReferences ?? new System.Collections.Generic.List<string>();
				report.AppendLine( $"{path}: references {(references.Count > 0 ? string.Join( ", ", references ) : "nothing")}" );
				if ( !bundleCode )
				{
					await upload.PrePublish();
					var errs = upload.Manifest.Errors;
					report.AppendLine( $"{upload.TargetPackageIdent} ({settings.ProjectConfig.Type}, parent {settings.ProjectConfig.GetMetaOrDefault( "ParentPackage", "-" )}): {upload.Manifest.Assets.Count} files, {upload.MissingFileCount} to upload ({upload.MissingFileSize.FormatBytes()}), {errs.Count} errors" );
					foreach ( var e in errs ) report.AppendLine( $"  error: {e}" );
					if ( !publish )
					{
						foreach ( var f in upload.Manifest.Assets ) report.AppendLine( $"  {f.Name} ({((long)f.Size).FormatBytes()})" );
						continue;
					}
					if ( errs.Count > 0 ) continue;
					upload.OnProgressChanged = () => { };
					if ( upload.MissingFileCount > 0 ) await upload.UploadFiles();
					await upload.Publish();
					report.AppendLine( "  published" );
					continue;
				}

				// An entity that does include code gets it compiled, as the publish wizard's Compile step does: this
				// project and every library compiled for release, each as .bin/<assembly>.cll, plus the load order.
				// Single-asset publishing never includes source files.
				var codeProject = asset.Publishing.CreateTemporaryProject( Project.Current.RootDirectory );
				var originalType = codeProject.Config.Type;
				CompilerOutput[] compiled;
				try
				{
					codeProject.Config.Type = "game";
					compiled = await EditorUtility.Projects.Compile( codeProject, null );
				}
				finally
				{
					codeProject.Config.Type = originalType;
				}

				if ( compiled is null || compiled.Length == 0 || compiled.Any( x => !x.Successful ) )
				{
					report.AppendLine( $"{path}: compile failed ({string.Join( ", ", compiled?.Where( x => !x.Successful ).Select( x => x.Compiler.AssemblyName ) ?? new[] { "no code" } )})" );
					continue;
				}

				await upload.AddFile( System.Text.Json.JsonSerializer.Serialize( compiled.Select( x => x.Compiler.AssemblyName ).ToList() ), ".bin/manifest.json" );
				foreach ( var assembly in compiled )
				{
					await upload.AddFile( assembly.XmlDocumentation ?? "", $".bin/{assembly.Compiler.AssemblyName}.xml" );
					await upload.AddFile( assembly.Archive.Serialize(), $".bin/{assembly.Compiler.AssemblyName}.cll" );
				}

				// Razor components load their .razor.scss/.css stylesheets at runtime from the package filesystem,
				// so bundle stylesheets from this project and all referenced libraries alongside the compiled code.
				var codeRoots = new List<string>();
				if ( Project.Current?.GetCodePath() is string currentCodePath && !string.IsNullOrEmpty( currentCodePath ) )
					codeRoots.Add( currentCodePath );
				foreach ( var library in LibrarySystem.All )
				{
					if ( library?.Project?.GetCodePath() is string libCodePath && !string.IsNullOrEmpty( libCodePath ) )
						codeRoots.Add( libCodePath );
				}

				var addedStyles = new HashSet<string>( StringComparer.OrdinalIgnoreCase );
				foreach ( var codeRoot in codeRoots )
				{
					foreach ( var file in EnumerateStylesheets( codeRoot ) )
					{
						var relativePath = Path.GetRelativePath( codeRoot, file ).Replace( '\\', '/' ).ToLowerInvariant();
						if ( !addedStyles.Add( relativePath ) ) continue;
						await upload.AddFile( await System.IO.File.ReadAllBytesAsync( file ), relativePath );
					}
				}
				report.AppendLine( $"{path}: code {string.Join( ", ", compiled.Select( x => x.Compiler.AssemblyName ) )}" );

				await upload.PrePublish();

				var errors = upload.Manifest.Errors;
				var files = upload.Manifest.Assets;
				report.AppendLine( $"{upload.TargetPackageIdent} ({settings.ProjectConfig.Type}, parent {settings.ProjectConfig.GetMetaOrDefault( "ParentPackage", "-" )}): {files.Count} files, {upload.MissingFileCount} to upload ({upload.MissingFileSize.FormatBytes()}), {errors.Count} errors" );
				foreach ( var e in errors ) report.AppendLine( $"  error: {e}" );

				if ( !publish )
				{
					foreach ( var f in files ) report.AppendLine( $"  {f.Name} ({((long)f.Size).FormatBytes()})" );
					continue;
				}

				if ( errors.Count > 0 ) continue;
				// the publisher reports upload progress through this, and throws if nothing's listening
				upload.OnProgressChanged = () => { };
				if ( upload.MissingFileCount > 0 ) await upload.UploadFiles();
				await upload.Publish();
				report.AppendLine( $"  published" );
			}
			catch ( System.Exception e )
			{
				report.AppendLine( $"{path}: {e.GetType().Name}: {e.Message}" );
			}
		}

		if ( publish ) EditorUtility.ClearPackageCache();
		return report.ToString();
	}

	static IEnumerable<string> EnumerateStylesheets( string root )
	{
		if ( string.IsNullOrEmpty( root ) || !Directory.Exists( root ) )
			yield break;

		var dirs = new Stack<string>();
		dirs.Push( root );
		while ( dirs.Count > 0 )
		{
			var dir = dirs.Pop();
			foreach ( var file in Directory.EnumerateFiles( dir ) )
			{
				var ext = Path.GetExtension( file );
				if ( ext.Equals( ".scss", StringComparison.OrdinalIgnoreCase ) || ext.Equals( ".css", StringComparison.OrdinalIgnoreCase ) )
					yield return file;
			}
			foreach ( var subDir in Directory.EnumerateDirectories( dir ) )
			{
				var name = Path.GetFileName( subDir );
				if ( string.IsNullOrEmpty( name ) || name.StartsWith( '.' ) || name.Equals( "obj", StringComparison.OrdinalIgnoreCase ) || name.Equals( "bin", StringComparison.OrdinalIgnoreCase ) )
					continue;
				dirs.Push( subDir );
			}
		}
	}
}
