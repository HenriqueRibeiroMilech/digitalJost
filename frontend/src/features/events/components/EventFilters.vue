<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import MultiSelect from '@/volt/MultiSelect.vue'
import { defaultEventStatuses, eventStatusOptions } from '../statuses'
import type { EventFilters, EventStatus } from '../types'

const emit = defineEmits<{ change: [filters: EventFilters] }>()
const search = ref('')
const statuses = ref<EventStatus[]>([...defaultEventStatuses])
const isDefault = computed(() => !search.value && statuses.value.length === defaultEventStatuses.length
  && defaultEventStatuses.every(status => statuses.value.includes(status)))

function emitFilters() {
  emit('change', {
    search: search.value.trim(),
    statuses: eventStatusOptions.map(option => option.value).filter(value => statuses.value.includes(value)),
  })
}

watch(search, (_value, _previous, onCleanup) => {
  const timer = window.setTimeout(emitFilters, 300)
  onCleanup(() => window.clearTimeout(timer))
})
watch(statuses, emitFilters, { deep: true })

function reset() {
  search.value = ''
  statuses.value = [...defaultEventStatuses]
  emitFilters()
}
</script>

<template>
  <form role="search" aria-label="Filtrar eventos" class="mb-6 rounded-dj-card border border-dj-border bg-dj-surface p-4 shadow-dj-card sm:p-5"
    @submit.prevent="emitFilters">
    <div class="grid grid-cols-1 items-end gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,22rem)_auto]">
      <div>
        <label for="events-search" class="mb-2 block text-xs font-semibold text-dj-muted">Pesquisar por título</label>
        <div class="relative">
          <i class="pi pi-search pointer-events-none absolute top-1/2 left-3 z-1 -translate-y-1/2 text-sm text-dj-muted" aria-hidden="true" />
          <InputText id="events-search" v-model="search" type="search" :maxlength="120"
            placeholder="Busque pelo título do evento" pt:root:class="w-full rounded-xl py-3 pl-10" />
        </div>
      </div>
      <div>
        <label id="events-status-label" for="events-status" class="mb-2 block text-xs font-semibold text-dj-muted">Status</label>
        <MultiSelect v-model="statuses" :options="eventStatusOptions" option-label="label" option-value="value"
          input-id="events-status" aria-labelledby="events-status-label" placeholder="Todos os status"
          :show-toggle-all="false" pt:root:class="w-full rounded-xl" pt:label:class="py-3" />
      </div>
      <Button type="button" label="Restaurar padrão" icon="pi pi-refresh" outlined
        :disabled="isDefault" pt:root:class="rounded-xl py-3" @click="reset" />
    </div>
    <p class="mt-3 text-xs leading-5 text-dj-muted">Selecione um ou mais status. Sem seleção, todos são exibidos.</p>
  </form>
</template>
