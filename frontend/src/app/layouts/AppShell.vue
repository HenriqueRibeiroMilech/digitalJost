<template>
  <div class="min-h-screen bg-dj-canvas">
    <header class="bg-dj-brand text-white">
      <div class="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <span class="border-l-4 border-dj-accent pl-3 text-lg font-semibold">
          Digital JOST
        </span>
        <a href="/" class="rounded px-2 py-1 text-sm underline underline-offset-4">
          Voltar ao portal
        </a>
      </div>
    </header>
    <main class="mx-auto max-w-[1200px] px-4 py-8 sm:px-6">
      <slot />
    </main>
  </div>
</template>