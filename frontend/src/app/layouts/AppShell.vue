<template>
  <div class="min-h-screen bg-dj-canvas">
    <header class="dj-app-header">
      <div class="dj-container flex min-h-20 flex-wrap items-center justify-between gap-3 py-4">
        <div class="dj-app-brand">
          <span class="inline-flex size-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/15" aria-hidden="true">
            <i class="pi pi-th-large text-lg" />
          </span>
          <span class="text-xl font-medium">Digital <strong class="font-bold">JOST</strong></span>
        </div>
        <nav aria-label="Navegação principal">
          <a href="/" class="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-2 text-sm
            transition-colors hover:border-white/40 hover:bg-white/10 focus-visible:outline-white">
            <i class="pi pi-arrow-up-left text-xs" aria-hidden="true" />
            <span>Voltar ao portal</span>
          </a>
        </nav>
      </div>
    </header>
    <main id="app-main" class="dj-container py-8 sm:py-10">
      <slot />
    </main>
  </div>
</template>
