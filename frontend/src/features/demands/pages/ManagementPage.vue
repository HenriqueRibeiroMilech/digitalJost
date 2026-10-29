<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import PageHeader from '@/shared/components/PageHeader.vue'
import CardGrid from '@/shared/components/CardGrid.vue'
import CardGridSkeleton from '@/shared/components/CardGridSkeleton.vue'
import RequestState from '@/shared/components/RequestState.vue'
import ListHeader from '@/shared/components/ListHeader.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import { usePagination } from '@/shared/composables/usePagination'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import RequestCard from '../components/RequestCard.vue'
import RequestDetail from '../components/RequestDetail.vue'
import DemandBoard from '../components/DemandBoard.vue'
import { demandsApi } from '../api'
import type { ManagementFilters } from '../types'

const route = useRoute()
const router = useRouter()
const client = useQueryClient()
const tab = computed(() => route.query.request || route.query.tab === 'solicitacoes' ? 'solicitacoes' : 'demandas')
const busy = ref(false)
const feedback = ref('')
const pageElement = ref<HTMLElement | null>(null)
const { page, perPage, resetPage } = usePagination()
const search = ref('')
const kind = ref<ManagementFilters['entry_kind']>('todos')
const status = ref<ManagementFilters['status']>('pendentes')
const filters = ref<ManagementFilters>({ search: '', entry_kind: 'todos', status: 'pendentes' })
const kindOptions = [
  { label: 'Todos os tipos', value: 'todos' }, { label: 'Demandas', value: 'demanda' }, { label: 'Relatos de erro', value: 'erro' },
]
const statusOptions = [
  { label: 'Pendentes de análise', value: 'pendentes' }, { label: 'Em análise', value: 'em_analise' },
  { label: 'Aguardando informações', value: 'aguardando_informacoes' }, { label: 'Aceitas', value: 'a_fazer' },
  { label: 'Recusadas', value: 'recusado' }, { label: 'Todas as situações', value: 'todos' },
]
function parseId(value: unknown) {
  return typeof value === 'string' && /^[1-9]\d{0,9}$/.test(value) && Number(value) <= 2147483647 ? Number(value) : null
}
const selectedId = ref<number | null>(parseId(route.query.request))
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: ['demands', 'management', 'list', page, filters],
  queryFn: () => demandsApi.managementList(page.value, perPage, filters.value),
  enabled: computed(() => tab.value === 'solicitacoes'), retry: false, refetchOnWindowFocus: false,
})
watch(data, result => {
  if (result) page.value = Math.min(page.value, Math.max(1, Math.ceil(result.total / perPage)))
})
watch(() => route.query.request, value => { selectedId.value = parseId(value) })
onBeforeRouteLeave(() => !busy.value)
onBeforeRouteUpdate(() => !busy.value)

function changeTab(value: 'demandas' | 'solicitacoes') {
  if (busy.value) return
  feedback.value = ''
  void router.replace({ query: { ...route.query, tab: value, request: undefined, work: undefined } })
}
function applyFilters() {
  resetPage()
  filters.value = { search: search.value.trim(), entry_kind: kind.value, status: status.value }
}
function openRequest(id: number) {
  feedback.value = ''
  void router.replace({ query: { ...route.query, tab: 'solicitacoes', request: String(id) } })
}
function reviewed() {
  feedback.value = 'Decisão registrada. O resultado está disponível nos detalhes e no histórico da solicitação.'
  void client.invalidateQueries({ queryKey: ['demands', 'management', 'list'] })
  void client.invalidateQueries({ queryKey: ['demands', 'list'] })
  void client.invalidateQueries({ queryKey: ['demands', 'work'] })
}
async function detailClosed() {
  const previous = selectedId.value
  selectedId.value = null
  await router.replace({ query: { ...route.query, request: undefined } })
  await nextTick()
  const card = previous ? document.getElementById('request-open-' + previous) : null
  const target = card ?? pageElement.value
  target?.focus()
}
</script>

<template>
  <section ref="pageElement" tabindex="-1" aria-labelledby="management-title">
    <PageHeader id="management-title" title="Gerenciador de demandas" eyebrow="Transformação Digital" icon="pi pi-briefcase"
      description="Organize as demandas da equipe, consulte avisos e analise as solicitações recebidas." />
    <nav aria-label="Áreas do gerenciador" class="mb-6 flex flex-wrap gap-2 rounded-2xl border border-dj-border bg-dj-surface p-2">
      <Button type="button" label="Demandas" icon="pi pi-briefcase" :outlined="tab !== 'demandas'" :disabled="busy"
        :aria-current="tab === 'demandas' ? 'page' : undefined" aria-controls="management-demands"
        pt:root:class="rounded-xl px-5 py-3" @click="changeTab('demandas')" />
      <Button type="button" label="Solicitações" icon="pi pi-inbox" :outlined="tab !== 'solicitacoes'" :disabled="busy"
        :aria-current="tab === 'solicitacoes' ? 'page' : undefined" aria-controls="management-requests"
        pt:root:class="rounded-xl px-5 py-3" @click="changeTab('solicitacoes')" />
    </nav>
    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-5">{{ feedback }}</Message>
    <DemandBoard v-if="tab === 'demandas'" id="management-demands" @busy="busy = $event" />
    <section v-else id="management-requests" aria-label="Solicitações recebidas">
      <form role="search" aria-label="Filtrar solicitações recebidas" @submit.prevent="applyFilters"
        class="dj-filter-panel mb-5 grid items-end gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(10rem,13rem)_minmax(12rem,16rem)_auto]">
        <div>
          <label for="management-search" class="mb-2 block text-xs font-semibold text-dj-muted">Buscar por título ou número</label>
          <div class="relative">
            <i class="pi pi-search pointer-events-none absolute top-1/2 left-3 z-1 -translate-y-1/2 text-sm text-dj-muted" aria-hidden="true" />
            <InputText id="management-search" v-model="search" type="search" :maxlength="250" placeholder="Título ou #número"
              pt:root:class="w-full rounded-xl py-3 pl-10" />
          </div>
        </div>
        <div>
          <label for="management-kind" class="mb-2 block text-xs font-semibold text-dj-muted">Tipo</label>
          <Select v-model="kind" input-id="management-kind" :options="kindOptions" option-label="label" option-value="value"
            pt:root:class="w-full rounded-xl" pt:label:class="py-3" />
        </div>
        <div>
          <label for="management-status" class="mb-2 block text-xs font-semibold text-dj-muted">Situação</label>
          <Select v-model="status" input-id="management-status" :options="statusOptions" option-label="label" option-value="value"
            pt:root:class="w-full rounded-xl" pt:label:class="py-3" />
        </div>
        <Button type="submit" label="Buscar" icon="pi pi-search" pt:root:class="rounded-xl py-3" />
      </form>
      <ListHeader id="management-results-title" title="Solicitações recebidas"
        :total="!isPending && !isError ? data?.total : undefined" total-label="Total de solicitações"
        description="Abra um card para consultar todos os dados e registrar sua decisão." />
      <RequestState :loading="isPending" :failed="isError" :error="error" :empty="data?.items.length === 0"
        loading-label="Carregando solicitações recebidas…" empty-title="Nenhuma solicitação encontrada"
        empty-description="Não há solicitações para os filtros selecionados. Ajuste os filtros ou consulte outra situação."
        error-message="Não foi possível carregar as solicitações recebidas." @retry="refetch()">
        <template #loading><CardGridSkeleton :count="12" compact /></template>
        <CardGrid>
          <RequestCard v-for="request in data?.items ?? []" :key="request.id" :request="request" management @open="openRequest(request.id)" />
        </CardGrid>
      </RequestState>
      <ListPagination v-if="data && !isPending && !isError" v-model:page="page" :per-page="perPage" :total="data.total" label="Páginas de solicitações recebidas" />
    </section>
    <RequestDetail v-if="selectedId" :key="selectedId" :id="selectedId" management @closed="detailClosed" @changed="reviewed" @busy="busy = $event" />
  </section>
</template>
