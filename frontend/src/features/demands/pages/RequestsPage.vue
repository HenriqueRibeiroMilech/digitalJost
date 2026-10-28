<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import PageHeader from '@/shared/components/PageHeader.vue'
import CardGrid from '@/shared/components/CardGrid.vue'
import CardGridSkeleton from '@/shared/components/CardGridSkeleton.vue'
import RequestState from '@/shared/components/RequestState.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import ListHeader from '@/shared/components/ListHeader.vue'
import { usePagination } from '@/shared/composables/usePagination'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import RequestForm from '../components/RequestForm.vue'
import RequestCard from '../components/RequestCard.vue'
import RequestDetail from '../components/RequestDetail.vue'
import { demandsApi } from '../api'
import type { RequestDetail as RequestData, RequestFilters } from '../types'

const route = useRoute()
const router = useRouter()
const client = useQueryClient()
const tab = computed(() => route.query.tab === 'minhas' || route.query.request ? 'minhas' : 'nova')
const busy = ref(false)
const detailBusy = ref(false)
const feedback = ref('')
const pageElement = ref<HTMLElement | null>(null)
const { page, perPage, resetPage } = usePagination()
const search = ref('')
const kind = ref<RequestFilters['entry_kind']>('todos')
const filters = ref<RequestFilters>({ search: '', entry_kind: 'todos' })
const filterOptions = [
  { label: 'Todos os tipos', value: 'todos' },
  { label: 'Demandas', value: 'demanda' },
  { label: 'Relatos de erro', value: 'erro' },
]
function parseId(value: unknown) {
  return typeof value === 'string' && /^[1-9]\d{0,9}$/.test(value) && Number(value) <= 2147483647 ? Number(value) : null
}
const selectedId = ref<number | null>(parseId(route.query.request))
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: ['demands', 'list', page, filters],
  queryFn: () => demandsApi.list(page.value, perPage, filters.value),
  enabled: computed(() => tab.value === 'minhas'), retry: false,
  refetchOnWindowFocus: false,
})
watch(data, result => {
  if (result) page.value = Math.min(page.value, Math.max(1, Math.ceil(result.total / perPage)))
})
watch(() => route.query.request, value => { selectedId.value = parseId(value) })
onBeforeRouteLeave(() => !busy.value && !detailBusy.value)
onBeforeRouteUpdate(() => !busy.value && !detailBusy.value)

function changeTab(value: 'nova' | 'minhas') {
  if (busy.value || detailBusy.value) return
  void router.replace({ query: { ...route.query, tab: value, request: undefined } })
}
function applyFilters() {
  resetPage()
  filters.value = { search: search.value.trim(), entry_kind: kind.value }
}
function openRequest(id: number) {
  void router.replace({ query: { ...route.query, tab: 'minhas', request: String(id) } })
}
async function saved(request: RequestData) {
  feedback.value = `Solicitação #${request.id} enviada com sucesso.`
  client.setQueryData(['demands', 'detail', request.id], request)
  search.value = ''
  kind.value = 'todos'
  applyFilters()
  await client.invalidateQueries({ queryKey: ['demands', 'list'] })
  changeTab('minhas')
  await nextTick()
  pageElement.value?.focus()
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
  <section ref="pageElement" tabindex="-1" aria-labelledby="requests-title">
    <PageHeader id="requests-title" title="Solicitações de demandas" eyebrow="Transformação Digital" icon="pi pi-lightbulb"
      description="Envie uma necessidade ou reporte um erro e acompanhe suas solicitações.">
      <template #actions>
        <a href="/demandas/solicitacoes?area=Transforma%C3%A7%C3%A3o%20Digital&amp;tab=minhas"
          class="rounded-lg px-3 py-2 text-sm text-dj-brand underline underline-offset-4">Consultar solicitações anteriores</a>
      </template>
    </PageHeader>
    <nav aria-label="Áreas das solicitações" class="mb-6 flex flex-wrap gap-2 rounded-2xl border border-dj-border bg-dj-surface p-2">
      <Button id="requests-new-action" type="button" label="Nova solicitação" icon="pi pi-plus" :outlined="tab !== 'nova'"
        :aria-current="tab === 'nova' ? 'page' : undefined" aria-controls="requests-new" :disabled="busy || detailBusy"
        pt:root:class="rounded-xl px-5 py-3" @click="changeTab('nova')" />
      <Button type="button" label="Minhas solicitações" icon="pi pi-inbox" :outlined="tab !== 'minhas'"
        :aria-current="tab === 'minhas' ? 'page' : undefined" aria-controls="requests-mine" :disabled="busy || detailBusy"
        pt:root:class="rounded-xl px-5 py-3" @click="changeTab('minhas')" />
    </nav>
    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-5">{{ feedback }}</Message>
    <section v-show="tab === 'nova'" id="requests-new" aria-label="Nova solicitação" class="rounded-dj-card border border-dj-border bg-dj-surface p-4 shadow-dj-card sm:p-6">
      <RequestForm @busy="busy = $event" @saved="saved" @inspect="changeTab('minhas')" />
    </section>
    <section v-show="tab === 'minhas'" id="requests-mine" aria-label="Minhas solicitações">
      <form role="search" aria-label="Filtrar solicitações"
        class="dj-filter-panel mb-5 grid items-end gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(12rem,16rem)_auto]" @submit.prevent="applyFilters">
        <div>
          <label for="requests-search" class="mb-2 block text-xs font-semibold text-dj-muted">Buscar por título ou número</label>
          <div class="relative">
            <i class="pi pi-search pointer-events-none absolute top-1/2 left-3 z-1 -translate-y-1/2 text-sm text-dj-muted" aria-hidden="true" />
            <InputText id="requests-search" v-model="search" type="search" :maxlength="250" placeholder="Ex.: automatizar relatório"
              pt:root:class="w-full rounded-xl py-3 pl-10" />
          </div>
        </div>
        <div>
          <label for="requests-kind" class="mb-2 block text-xs font-semibold text-dj-muted">Tipo</label>
          <Select v-model="kind" input-id="requests-kind" :options="filterOptions" option-label="label" option-value="value"
            pt:root:class="w-full rounded-xl" pt:label:class="py-3" />
        </div>
        <Button type="submit" label="Buscar" icon="pi pi-search" pt:root:class="rounded-xl py-3" />
      </form>
      <ListHeader id="requests-results-title" title="Solicitações encontradas"
        :total="!isPending && !isError ? data?.total : undefined" total-label="Total de solicitações"
        description="Inclui as solicitações que você acompanha como contribuinte." />
      <RequestState :loading="isPending" :failed="isError" :error="error" :empty="data?.items.length === 0"
        loading-label="Carregando solicitações…" empty-title="Nenhuma solicitação encontrada"
        empty-description="Envie uma nova solicitação ou ajuste os filtros. Para consultar pedidos anteriores, use o link no cabeçalho."
        error-message="Não foi possível carregar suas solicitações." @retry="refetch()">
        <template #loading>
          <CardGridSkeleton :count="12" compact />
        </template>
        <CardGrid>
          <RequestCard v-for="request in data?.items ?? []" :key="request.id" :request="request" @open="openRequest(request.id)" />
        </CardGrid>
      </RequestState>
      <ListPagination v-if="data && !isError && !isPending" v-model:page="page" :per-page="perPage" :total="data.total" label="Páginas de solicitações" />
    </section>
    <RequestDetail v-if="selectedId" :key="selectedId" :id="selectedId" @closed="detailClosed"
      @changed="client.invalidateQueries({ queryKey: ['demands', 'list'] })" @busy="detailBusy = $event" />
  </section>
</template>
