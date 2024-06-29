<script lang='ts'>
	import { onMount } from "svelte";
	import { loader } from './loader';
	import { writable  } from 'svelte/store';
	import PdfViewer from '$lib/components/PdfViewer.svelte';

	// import { toast } from '@zerodevx/svelte-toast';
  
	let data: any; 
	let endpoint: string = 'http://127.0.0.1:8000';
	let api: string = 'upload-pdf-file';
	let loading = writable(false);
	let hasUploadedFile = writable(false);
	let uploadedFileLocalPath = writable(null);
	let url = writable(null);
	let base64Data = writable('');
  
	onMount(async () => {
	});

	async function uploadFile(e: any) {
	
		base64Data.set('');
		hasUploadedFile.set(false);
		loading.set(true);

		console.log(e.target.files[0])

		const file = e.target.files[0];
		const formData = new FormData();
		formData.append('uf', file);

		const res = await fetch(
			`${endpoint}/${api}`,
			{
				method: 'POST',
				body: formData
			}
		);

		// toast.push('File uploaded successfully!');

		if (res.ok) {
			data = await res.json();
			hasUploadedFile.set(true);
			const base64String: any = await pdfToBase64(file);
			base64Data.set(base64String);
			uploadedFileLocalPath.set(file.name);
			loading.set(false);
		} else {
			loading.set(false);
		}

	}

	const pdfToBase64 = (file: any) => {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onloadend = () => {
				const base64String = (reader.result as string).split(',')[1];
				resolve(base64String);
			};
			reader.onerror = (error) => {
				reject(error);
			};
			reader.readAsDataURL(file);
		});
	};
  
</script>
  
<svelte:head>
	<title>About</title>
	<meta name="description" content="About this app" />
</svelte:head>

<div class='main'> 
	<div class='left-col'>
		<label for="file-upload" class="custom-file-upload">
			<p class='file-upload-text'>
				Upload PDF
			</p>
		</label>
		<input id="file-upload" type="file" accept=".pdf" on:change={e => uploadFile(e)} />
		{#if $hasUploadedFile}
			<h4>
				{#if $uploadedFileLocalPath}
					{$uploadedFileLocalPath}
				{:else}
					'No file uploaded'
				{/if}
			</h4>
			<div class='pdf'> 
				<PdfViewer data={$base64Data} />
			</div>		
		{/if}
	</div>

	{#if $hasUploadedFile}
		<div class='right-col'>
			<h2 class='right-col-title'>Chat</h2>
			<div class='chat-bar'>
				<input type="text" placeholder="Type your prompt..." class="chat-input">
				<button class="send-button">Send</button>
			</div>
		</div>
	{/if}
</div>

{#if $loading}
	{#await loader}
		<div>Loading...</div>
	{/await}
{/if}

  <style>

	.main {
        display: flex;
		height: 100%;
		max-height: 100%;
		min-height: 100%;
		overflow: hidden;
    }

	input[type="file"] {
	  display: none;
	}
  
	/* https://stackoverflow.com/questions/572768/styling-an-input-type-file-button */
	.custom-file-upload {
		display: inline-block;
		padding: 6px 12px;
		cursor: pointer;
		background-color: var(--green-200);
		text-emphasis-color: var(--green-200);
		border-radius: 8px;
		border-top: 0;
		margin-top: .5rem;
		margin-bottom: .5rem;
	}

	h4 {
		margin-bottom: 1rem;
		margin-left: 6rem;
		margin-right: 6rem;
		text-align: left;
	}
  
	.file-upload-text {
		color: var(--sand-200);
	}
  
	.left-col {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 87vh;
		overflow: hidden;
        width: 50%;
    }

    .right-col {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: start;
        height: 87vh;
        width: 50%;
    }

	.right-col-title {
		margin-top: 2rem;
	}

	.pdf {
		min-height: 10%;
		max-height: 82vh;
		min-width: 20%;
		max-width: 90%;
		z-index: 10;
		background-color: var(--purple-100);
		border: 12px solid var(--purple-100);
		/* rounded: 8px; */
		border-radius: 8px;
	}
  
	.chat-bar {
		position: absolute;
		bottom: 10%;
		width: 40%;
		background-color: var(--sand-200);
		padding: 1rem;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Optional: Adds a subtle shadow */
		display: flex;
		/* align-items: center; */
		justify-content: space-between;
		z-index: 20; /* Optional: Ensures it's above other elements */
	}
  
	.chat-input {
		flex: 1; /* Take up all available space */
		border: none; /* Remove the border */
		padding: 0.5rem; /* Add some padding */
		border-radius: 8px; /* Optional: Adds some border radius */
	}
  
	.send-button {
		padding: 0.5rem 1rem;
		border: none;
		border-radius: 8px;
		background-color: var(--purple-200);
		color: var(--sand-200);
		cursor: pointer;
		transition: background-color 0.3s ease;
		margin-left: 1rem;
	}
  
	.send-button:hover {
	  	background-color: var(--purple-300);
	}
  </style>
  