<script>
	import Header from './Header.svelte';
	import './styles.css';
	// import { SvelteToast } from '@zerodevx/svelte-toast'

  </script>
  
  <div class="app">
	
	<Header />
  
	<main class='main'>
	  <slot />
	  <!-- <SvelteToast /> -->
	</main>
  
	<footer>
	  <p>Visit <a href="https://outerbounds.com/get-started/">outerbounds.com</a> to build hundreds of apps like this in your cloud account</p>
	</footer>
  </div>
  
  <style>

	.app {
	  display: flex;
	  flex-direction: column;
	  background-color: var(--sand-100);
	}
  
	main {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 1rem;
		box-sizing: border-box;
    }
  
	footer {
		position: absolute;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		padding: 12px;
		font-style: italic;
		background-color: var(--sand-100);
		position: sticky;
		bottom: 0;
		width: 100%;
	}
  
	footer a {
	  font-weight: bold;
	}
  
	@media (min-width: 480px) {
	  footer {
		padding: 12px 0;
	  }
	}
  </style>
  