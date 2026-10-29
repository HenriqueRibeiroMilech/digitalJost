<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import CardGrid from '@/shared/components/CardGrid.vue'
import CardGridSkeleton from '@/shared/components/CardGridSkeleton.vue'
import ListHeader from '@/shared/components/ListHeader.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import RequestState from '@/shared/components/RequestState.vue'
import { usePagination } from '@/shared/composables/usePagination'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import { workApi } from '../api'
import { workKindOptions } from '../presentation'
import type { WorkDetail, WorkFilters, WorkKind } from '../types'
import DemandCard from './DemandCard.vue'
import DemandCreateDialog from './DemandCreateDialog.vue'
import DemandDetail from './DemandDetail.vue'

const emit = defineEmits<{ busy: [value: boolean] }>()
const route = useRoute()
const router = useRouter()
const client = useQueryClient()
const busy = ref(false)
const creating = ref(false)
const feedback = ref('')
const root = ref<HTMLElement | null>(null)
const search = ref('')
const appliedSearch = ref('')
const kind = ref<WorkFilters['kind']>('todos')
const appliedKind = ref<WorkFilters['kind']>('todos')
const { page, perPage, resetPage } = usePagination()
const board = useQuery({ queryKey: ['demands', 'work', 'board'], queryFn: workApi.board,
  retry: false, refetchOnWindowFocus: false })
const notices = computed(() => route.query.board === 'avisos')
const ownerId = computed(() => {
  if (typeof route.query.owner === 'string' && route.query.owner) return route.query.owner
  const data = board.data.value
  return data?.owners.find(owner => owner.id === data.actor_id)?.id ?? data?.owners[0]?.id ?? data?.actor_id ?? null
})
const ownerName = computed(() => board.data.value?.owners.find(owner => owner.id === ownerId.value)?.name ?? 'Responsável')
const filters = computed<WorkFilters>(() => ({ view: notices.value ? 'notices' : 'users', owner_id: ownerId.value,
  search: appliedSearch.value, kind: appliedKind.value }))
const list = useQuery({ queryKey: ['demands', 'work', 'list', filters, page],
  queryFn: () => workApi.list(page.value, perPage, filters.value),
  enabled: computed(() => Boolean(board.data.value) && !board.isError.value), retry: false, refetchOnWindowFocus: false })
const typeOptions = [{ value: 'todos', label: 'Todos os tipos' }, ...workKindOptions.filter(option => option.value !== 'aviso')]
function parseId(value: unknown) {
  return typeof value === 'string' && /^[1-9]\d{0,9}$/.test(value) && Number(value) <= 2147483647 ? Number(value) : null
}
const selectedId = ref<number | null>(parseId(route.query.work))
watch(() => route.query.work, value => { selectedId.value = parseId(value) })
watch(busy, value => emit('busy', value), { flush: 'sync' })
watch(list.data, result => {
  if (result) page.value = Math.min(page.value, Math.max(1, Math.ceil(result.total / perPage)))
})
async function selectOwner(id: string | null, showNotices = false) {
  if (busy.value) return
  feedback.value = ''
  resetPage()
  await router.replace({ query: { ...route.query, tab: 'demandas', board: showNotices ? 'avisos' : undefined,
    owner: showNotices ? undefined : id ?? undefined, work: undefined, request: undefined } })
}
function applyFilters() {
  resetPage()
  appliedSearch.value = search.value.trim()
  appliedKind.value = kind.value
}
function open(id: number) {
  feedback.value = ''
  void router.replace({ query: { ...route.query, tab: 'demandas', work: String(id), request: undefined } })
}
async function refreshBoard() {
  await Promise.all([
    client.invalidateQueries({ queryKey: ['demands', 'work', 'board'] }),
    client.invalidateQueries({ queryKey: ['demands', 'work', 'list'] }),
  ])
}
async function created(item: WorkDetail) {
  client.setQueryData(['demands', 'work', 'detail', item.id], item)
  search.value = ''
  kind.value = 'todos'
  applyFilters()
  await selectOwner(item.responsible_id, item.kind === 'aviso')
  feedback.value = `${item.kind === 'aviso' ? 'Aviso' : 'Demanda'} #${item.id} criado com sucesso.`
  await refreshBoard()
}
async function inspect(workType: WorkKind, owner: string) {
  search.value = ''
  kind.value = 'todos'
  appliedSearch.value = ''
  appliedKind.value = 'todos'
  await selectOwner(owner, workType === 'aviso')
  await refreshBoard()
  feedback.value = 'Confira o quadro antes de iniciar outro cadastro. O envio anterior pode ter sido confirmado.'
}
async function createClosed() {
  creating.value = false
  await nextTick()
  document.getElementById('work-new-action')?.focus()
}
async function detailClosed() {
  const previous = selectedId.value
  selectedId.value = null
  await router.replace({ query: { ...route.query, work: undefined } })
  await nextTick()
  const target = (previous ? document.getElementById('work-open-' + previous) : null) ?? root.value
  target?.focus()
}
</script>

<template>
  <section ref="root" tabindex="-1" aria-label="Quadro de demandas">
    <RequestState :loading="board.isPending.value" :failed="board.isError.value" :error="board.error.value" :empty="false"
      loading-label="Carregando responsáveis e avisos…" error-message="Não foi possível carregar o quadro." @retry="board.refetch()">
      <template #loading><CardGridSkeleton :count="12" compact /></template>
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p class="text-sm leading-6 text-dj-muted">Organize as demandas por responsável e consulte os avisos da equipe.</p>
        <Button v-if="board.data.value?.can_create" id="work-new-action" type="button" label="Nova demanda ou aviso" icon="pi pi-plus"
          :disabled="busy" aria-haspopup="dialog" @click="creating = true" />
      </div>
      <nav aria-label="Avisos e responsáveis" class="mb-5 flex flex-wrap gap-2 rounded-2xl border border-dj-border bg-dj-surface p-2">
        <Button type="button" :label="'Avisos (' + (board.data.value?.notice_total ?? 0) + ')'" icon="pi pi-megaphone" :outlined="!notices" :disabled="busy"
          :aria-current="notices ? 'page' : undefined" aria-controls="work-results" pt:root:class="rounded-xl px-4 py-3" @click="selectOwner(null, true)" />
        <Button v-for="owner in board.data.value?.owners ?? []" :key="owner.id" type="button" :label="owner.name + ' (' + owner.total + ')'" icon="pi pi-user"
          :outlined="notices || ownerId !== owner.id" :disabled="busy" :aria-current="!notices && ownerId === owner.id ? 'page' : undefined"
          aria-controls="work-results" pt:root:class="max-w-full rounded-xl px-4 py-3" pt:label:class="break-words whitespace-normal" @click="selectOwner(owner.id)" />
      </nav>
      <Message v-if="feedback" severity="info" role="status" class="mb-5">{{ feedback }}</Message>
      <form role="search" aria-label="Filtrar quadro" class="dj-filter-panel mb-5 grid items-end gap-4 sm:grid-cols-[minmax(0,1fr)_auto] lg:grid-cols-[minmax(0,1fr)_minmax(12rem,16rem)_auto]" @submit.prevent="applyFilters">
        <div>
          <label for="work-search" class="mb-2 block text-xs font-semibold text-dj-muted">Buscar por título ou número</label>
          <InputText id="work-search" v-model="search" type="search" :maxlength="250" placeholder="Título ou #número" class="w-full" pt:root:class="rounded-xl py-3" />
        </div>
        <div v-if="!notices">
          <label for="work-kind" class="mb-2 block text-xs font-semibold text-dj-muted">Tipo</label>
          <Select v-model="kind" input-id="work-kind" :options="typeOptions" option-label="label" option-value="value" class="w-full" pt:root:class="rounded-xl" pt:label:class="py-3" />
        </div>
        <Button type="submit" label="Buscar" icon="pi pi-search" pt:root:class="rounded-xl py-3" />
      </form>
      <section id="work-results" :aria-label="notices ? 'Avisos' : 'Demandas de ' + ownerName">
        <ListHeader id="work-results-title" :title="notices ? 'Avisos da equipe' : 'Demandas de ' + ownerName"
          :total="!list.isPending.value && !list.isError.value ? list.data.value?.total : undefined"
          :total-label="notices ? 'Total de avisos' : 'Total de demandas'" description="Abra um card para consultar as informações completas." />
        <RequestState :loading="list.isPending.value" :failed="list.isError.value" :error="list.error.value" :empty="list.data.value?.items.length === 0"
          loading-label="Carregando registros…" :empty-title="notices ? 'Nenhum aviso encontrado' : 'Nenhuma demanda encontrada'"
          empty-description="Cadastre um registro ou ajuste os filtros e o responsável selecionado." error-message="Não foi possível carregar os registros." @retry="list.refetch()">
          <template #loading><CardGridSkeleton :count="12" compact /></template>
          <CardGrid><DemandCard v-for="item in list.data.value?.items ?? []" :key="item.id" :item="item" @open="open(item.id)" /></CardGrid>
        </RequestState>
        <ListPagination v-if="list.data.value && !list.isError.value && !list.isPending.value" v-model:page="page" :per-page="perPage"
          :total="list.data.value.total" :label="notices ? 'Páginas de avisos' : 'Páginas de demandas'" />
      </section>
    </RequestState>
    <DemandCreateDialog v-if="creating" :owner-id="ownerId" @closed="createClosed" @busy="busy = $event" @saved="created" @inspect="inspect" />
    <DemandDetail v-if="selectedId" :key="selectedId" :id="selectedId" @closed="detailClosed" @busy="busy = $event"
      @changed="client.invalidateQueries({ queryKey: ['demands', 'work', 'list'] })" />
  </section>
</template>
