<script setup lang="ts">
import { computed, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import CardGrid from '@/shared/components/CardGrid.vue'
import CardGridSkeleton from '@/shared/components/CardGridSkeleton.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import RequestState from '@/shared/components/RequestState.vue'
import { usePagination } from '@/shared/composables/usePagination'
import Button from '@/volt/Button.vue'
import { workApi } from '../api'
import type { WorkFilters } from '../types'
import DemandCard from './DemandCard.vue'

const props = defineProps<{
  ownerId?: string
  title: string
  total: number
  expanded: boolean
  disabled: boolean
  search: string
  kind: WorkFilters['kind']
}>()
defineEmits<{ toggle: []; open: [id: number] }>()
const notices = computed(() => props.ownerId === undefined)
const id = computed(() => 'work-group-' + (props.ownerId === undefined ? 'notices'
  : 'owner-' + encodeURIComponent(props.ownerId).replace(/-/g, '%2D')))
const { page, perPage, resetPage } = usePagination()
const filters = computed<WorkFilters>(() => ({ view: notices.value ? 'notices' : 'users', owner_id: props.ownerId ?? null,
  search: props.search, kind: notices.value ? 'todos' : props.kind }))
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: ['demands', 'work', 'list', filters, page],
  queryFn: () => workApi.list(page.value, perPage, filters.value), enabled: computed(() => props.expanded),
  retry: false, refetchOnWindowFocus: false,
})
watch(() => [props.search, props.kind], resetPage)
watch(data, result => {
  if (result) page.value = Math.min(page.value, Math.max(1, Math.ceil(result.total / perPage)))
})
const demands = computed(() => data.value?.items.filter(item => item.kind !== 'atividade') ?? [])
const activities = computed(() => data.value?.items.filter(item => item.kind === 'atividade') ?? [])
const count = computed(() => data.value && !isPending.value && !isError.value ? data.value.total : props.total)
</script>

<template>
  <section :id="id" :aria-labelledby="id + '-title'" class="demand-group overflow-hidden rounded-dj-card border border-dj-border bg-dj-surface shadow-dj-card"
    :class="{ 'demand-group-notices': notices }">
    <h2>
      <Button type="button" class="demand-group-toggle w-full gap-3 px-4 py-4 text-left sm:px-5" :disabled="disabled"
        :aria-expanded="expanded" :aria-controls="id + '-content'" @click="$emit('toggle')">
        <span class="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-dj-surface text-dj-brand" aria-hidden="true">
          <i :class="notices ? 'pi pi-megaphone' : 'pi pi-user'" />
        </span>
        <span class="min-w-0 flex-1">
          <span :id="id + '-title'" class="block break-words text-sm font-semibold sm:text-base">{{ title }}</span>
          <span class="mt-1 block text-xs font-normal text-dj-muted">{{ notices ? 'Avisos da equipe' : 'Demandas e atividades' }}</span>
        </span>
        <span class="shrink-0 rounded-full border border-dj-border bg-dj-surface px-2.5 py-1 text-xs font-semibold text-dj-ink"
          :aria-label="count + (notices ? ' avisos' : ' demandas')">{{ count }}</span>
        <i :class="expanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="shrink-0 text-xs text-dj-muted" aria-hidden="true" />
      </Button>
    </h2>
    <div v-show="expanded" :id="id + '-content'" class="border-t border-dj-border p-4 sm:p-5">
      <RequestState :loading="isPending" :failed="isError" :error="error" :empty="data?.items.length === 0"
        loading-label="Carregando registros do grupo…" :empty-title="notices ? 'Nenhum aviso encontrado' : 'Nenhuma demanda encontrada'"
        empty-description="Não há registros para os filtros selecionados." error-message="Não foi possível carregar os registros deste grupo." @retry="refetch()">
        <template #loading><CardGridSkeleton :count="4" compact /></template>
        <template v-if="notices">
          <CardGrid><DemandCard v-for="item in data?.items ?? []" :key="item.id" :item="item" @open="$emit('open', item.id)" /></CardGrid>
        </template>
        <template v-else>
          <section v-if="demands.length" :aria-labelledby="id + '-demands'">
            <h3 :id="id + '-demands'" class="mb-4 border-l-3 border-dj-accent pl-3 text-xs font-semibold text-dj-brand">Projetos, melhorias e erros</h3>
            <CardGrid><DemandCard v-for="item in demands" :key="item.id" :item="item" @open="$emit('open', item.id)" /></CardGrid>
          </section>
          <section v-if="activities.length" :aria-labelledby="id + '-activities'" :class="{ 'mt-5 border-t border-dj-border pt-5': demands.length }">
            <h3 :id="id + '-activities'" class="mb-4 border-l-3 border-dj-accent pl-3 text-xs font-semibold text-dj-brand">Atividades</h3>
            <CardGrid><DemandCard v-for="item in activities" :key="item.id" :item="item" @open="$emit('open', item.id)" /></CardGrid>
          </section>
        </template>
      </RequestState>
      <ListPagination v-if="data && !isPending && !isError" v-model:page="page" :per-page="perPage" :total="data.total" :label="'Páginas de ' + title" />
    </div>
  </section>
</template>

<style scoped>
.demand-group {
  --demand-group-accent: var(--color-dj-brand);
}
.demand-group-notices {
  --demand-group-accent: var(--color-dj-accent);
}
.demand-group-toggle {
  border: 0;
  color: var(--color-dj-ink);
  background: linear-gradient(120deg,
    color-mix(in srgb, var(--demand-group-accent) 12%, var(--color-dj-surface)), var(--color-dj-surface) 90%);
}
.demand-group-toggle:enabled:hover {
  background: color-mix(in srgb, var(--demand-group-accent) 14%, var(--color-dj-surface));
}
.demand-group-toggle:focus-visible {
  outline: 2px solid var(--color-dj-brand);
  outline-offset: -3px;
}
</style>
