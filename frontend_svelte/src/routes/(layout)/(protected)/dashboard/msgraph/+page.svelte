<script lang="ts">
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import Heading from '$components/Heading.svelte';

	let { data }: { data: PageData } = $props();
	// TBD refactor using sessionData
	const account = data.account;
	const userProfile = data.userProfile;
	const userPicture = data.userPicture;
	//  This is the raw data fo the file - try demonstrating with a text file or md-file!
	console.log('ms_graph_me - userPicture');
	console.log(userPicture);

	let userPictureURL: string | undefined = $state(undefined);
	onMount(async () => {
		// this call does not have any authentication - remove it!
		const response = await fetch('/api/v1/user/me/picture', { method: 'GET' });
		if (!response.ok && response.status !== 200) {
			console.log('layout - userPictureURL - response not ok');
		} else {
			const pictureBlob = await response.blob();
			if (pictureBlob.size === 0) {
				console.log('layout - userPictureURL - no User picture available');
			} else {
				userPictureURL = URL.createObjectURL(pictureBlob);
			}
		}
	});
</script>

<Heading>First: Directly from SvelteAPI (works also without client side JavaScript):</Heading>
<Heading>Second: Passed through server load function and uses client side JavaScript:</Heading>
<!-- TBD: needs a check if user is logged in -> using store data?  -->
<img class="rounded-full" src="/api/v1/user/me/picture" alt="you" />

<!-- TBD: remove the following one: -->
{#if userPictureURL}
	<img class="h-100 w-100" src={userPictureURL} alt="you" />
{/if}

<Heading>Microsoft User Profile on DTU Tenant</Heading>
<code><pre>{JSON.stringify(userProfile, null, ' ')}</pre></code>

<Heading>Azure Account</Heading>
<code><pre>{JSON.stringify(account, null, ' ')}</pre></code>
