<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import PageHeader from '@/shared/components/PageHeader.vue'
import CardGrid from '@/shared/components/CardGrid.vue'
import RequestState from '@/shared/components/RequestState.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import { usePagination } from '@/shared/composables/usePagination'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import Skeleton from '@/volt/Skeleton.vue'
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
    <PageHeader id="requests-title" title="Solicitações de demandas" eyebrow="Transformação Digital"
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
      <form class="mb-6 grid gap-4 rounded-2xl border border-dj-border bg-dj-surface p-4 sm:grid-cols-[1fr_16rem_auto]" @submit.prevent="applyFilters">
        <div>
          <label for="requests-search" class="mb-2 block text-sm font-medium">Buscar por título ou número</label>
          <InputText id="requests-search" v-model="search" :maxlength="250" placeholder="Ex.: automatizar relatório"
            class="w-full" pt:root:class="rounded-xl" />
        </div>
        <div>
          <label for="requests-kind" class="mb-2 block text-sm font-medium">Tipo</label>
          <Select v-model="kind" input-id="requests-kind" :options="filterOptions" option-label="label" option-value="value"
            class="w-full" pt:root:class="rounded-xl" />
        </div>
        <Button type="submit" label="Buscar" icon="pi pi-search" class="self-end" pt:root:class="rounded-xl" />
      </form>
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-sm font-semibold">Solicitações encontradas <span v-if="data && !isError" class="ml-2 rounded-full border border-dj-border bg-dj-surface px-2.5 py-1 text-xs">{{ data.total }}</span></h2>
        <p class="text-xs text-dj-muted">Inclui as solicitações que você acompanha como contribuinte.</p>
      </div>
      <RequestState :loading="isPending" :failed="isError" :error="error" :empty="data?.items.length === 0"
        loading-label="Carregando solicitações…" empty-title="Nenhuma solicitação encontrada"
        empty-description="Envie uma nova solicitação ou ajuste os filtros. Para consultar pedidos anteriores, use o link no cabeçalho."
        error-message="Não foi possível carregar suas solicitações." @retry="refetch()">
        <template #loading>
          <CardGrid>
            <div v-for="index in 12" :key="index" class="rounded-dj-card border border-dj-border bg-dj-surface p-5 shadow-dj-card">
              <Skeleton width="3rem" height="3rem" border-radius="0.75rem" />
              <Skeleton width="85%" height="3rem" class="mt-4" />
              <Skeleton width="100%" height="6rem" class="mt-4" />
              <Skeleton width="100%" height="2rem" class="mt-4" />
            </div>
          </CardGrid>
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
