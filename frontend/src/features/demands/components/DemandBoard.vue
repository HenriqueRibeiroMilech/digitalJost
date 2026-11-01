<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import CardGridSkeleton from '@/shared/components/CardGridSkeleton.vue'
import ListHeader from '@/shared/components/ListHeader.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import { workApi } from '../api'
import { noticeStateOptions, workKindOptions, workStatusOptions } from '../presentation'
import type { WorkDetail, WorkFilters, WorkKind } from '../types'
import DemandGroup from './DemandGroup.vue'
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
const status = ref<WorkFilters['status']>('ativos')
const difficulty = ref<WorkFilters['difficulty']>('todas')
const sort = ref<WorkFilters['sort']>('priority')
const noticeState = ref<WorkFilters['notice_state']>('visible')
const appliedStatus = ref(status.value)
const appliedDifficulty = ref(difficulty.value)
const appliedSort = ref(sort.value)
const appliedNoticeState = ref(noticeState.value)
const boardFilters = computed<WorkFilters>(() => ({ view: 'users', owner_id: null, search: appliedSearch.value,
  kind: appliedKind.value, status: appliedStatus.value, difficulty: appliedDifficulty.value,
  sort: appliedSort.value, notice_state: appliedNoticeState.value }))
const board = useQuery({ queryKey: ['demands', 'work', 'board', boardFilters], queryFn: () => workApi.board(boardFilters.value),
  placeholderData: previous => previous, retry: false, refetchOnWindowFocus: false,
  refetchInterval: computed<number | false>(() => busy.value ? false : 60_000), refetchIntervalInBackground: false })
const ownerFilter = computed(() => typeof route.query.owner === 'string' && route.query.owner ? route.query.owner : null)
const selectedOwner = ref<string | null>(ownerFilter.value)
const ownerId = computed(() => ownerFilter.value ?? board.data.value?.actor_id ?? null)
const groups = computed(() => board.data.value?.owners.filter(owner => owner.total > 0
  && (!ownerFilter.value || owner.id === ownerFilter.value)).sort((left, right) => left.name.localeCompare(right.name, 'pt-BR')) ?? [])
const total = computed(() => groups.value.reduce((sum, group) => sum + group.total, 0))
const collapsed = ref(new Set<string>())
const noticesExpanded = ref(true)
let initialized = false
watch(board.data, result => {
  if (!result || initialized) return
  noticesExpanded.value = result.notice_total > 0 || route.query.board === 'avisos'
  const own = result.owners.find(owner => owner.id === result.actor_id && owner.total > 0)
  if (route.query.board === 'avisos' || (own && !ownerFilter.value)) {
    collapsed.value = new Set(result.owners.filter(owner => route.query.board === 'avisos' || owner.id !== result.actor_id).map(owner => owner.id))
  }
  initialized = true
}, { immediate: true })
watch(ownerFilter, value => { selectedOwner.value = value })
function toggleOwner(id: string) {
  if (busy.value) return
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}
async function showCreatedGroup(owner: string, notice: boolean) {
  if (busy.value) return
  collapsed.value = new Set([...collapsed.value].filter(id => id !== owner))
  if (notice) noticesExpanded.value = true
  selectedOwner.value = null
  await router.replace({ query: { ...route.query, tab: 'demandas', owner: undefined,
    board: undefined, work: undefined, request: undefined } })
}
const typeOptions = [{ value: 'todos', label: 'Todos os tipos' }, ...workKindOptions.filter(option => option.value !== 'aviso')]
function parseId(value: unknown) {
  return typeof value === 'string' && /^[1-9]\d{0,9}$/.test(value) && Number(value) <= 2147483647 ? Number(value) : null
}
const selectedId = ref<number | null>(parseId(route.query.work))
watch(() => route.query.work, value => { selectedId.value = parseId(value) })
watch(busy, value => emit('busy', value), { flush: 'sync' })
function applyFilters() {
  if (busy.value) return
  appliedSearch.value = search.value.trim()
  appliedKind.value = kind.value
  appliedStatus.value = status.value
  appliedDifficulty.value = difficulty.value
  appliedSort.value = sort.value
  appliedNoticeState.value = noticeState.value
  collapsed.value = new Set()
  noticesExpanded.value = true
  feedback.value = ''
  void router.replace({ query: { ...route.query, owner: selectedOwner.value ?? undefined, board: undefined } })
}
function clearFilters() {
  search.value = ''
  kind.value = 'todos'
  selectedOwner.value = null
  status.value = 'ativos'
  difficulty.value = 'todas'
  sort.value = 'priority'
  noticeState.value = 'visible'
  applyFilters()
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
  appliedSearch.value = ''
  appliedKind.value = 'todos'
  status.value = appliedStatus.value = 'ativos'
  difficulty.value = appliedDifficulty.value = 'todas'
  sort.value = appliedSort.value = 'priority'
  noticeState.value = appliedNoticeState.value = 'visible'
  await showCreatedGroup(item.responsible_id, item.kind === 'aviso')
  feedback.value = `${item.kind === 'aviso' ? 'Aviso' : 'Demanda'} #${item.id} criado com sucesso.`
  await refreshBoard()
}
async function inspect(workType: WorkKind, owner: string) {
  search.value = ''
  kind.value = 'todos'
  appliedSearch.value = ''
  appliedKind.value = 'todos'
  status.value = appliedStatus.value = 'ativos'
  difficulty.value = appliedDifficulty.value = 'todas'
  noticeState.value = appliedNoticeState.value = 'all'
  await showCreatedGroup(owner, workType === 'aviso')
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
        <p class="text-sm leading-6 text-dj-muted">Cadastre uma demanda ou aviso e acompanhe o quadro da equipe.</p>
        <Button v-if="board.data.value?.can_create" id="work-new-action" type="button" label="Nova demanda ou aviso" icon="pi pi-plus"
          :disabled="busy" aria-haspopup="dialog" @click="creating = true" />
      </div>
      <Message v-if="feedback" severity="info" role="status" class="mb-5">{{ feedback }}</Message>
      <form role="search" aria-label="Filtrar quadro" class="dj-filter-panel mb-5 grid items-end gap-4 sm:grid-cols-2 xl:grid-cols-4" @submit.prevent="applyFilters">
        <div>
          <label for="work-search" class="mb-2 block text-xs font-semibold text-dj-muted">Buscar por título ou número</label>
          <InputText id="work-search" v-model="search" type="search" :maxlength="250" :disabled="busy" placeholder="Título ou #número" class="w-full" pt:root:class="rounded-xl py-3" />
        </div>
        <div>
          <label for="work-owner" class="mb-2 block text-xs font-semibold text-dj-muted">Responsável</label>
          <Select v-model="selectedOwner" input-id="work-owner" :options="board.data.value?.owners ?? []" option-label="name" option-value="id"
            filter show-clear :disabled="busy" placeholder="Todos os responsáveis" class="w-full" pt:root:class="rounded-xl" pt:label:class="py-3" />
        </div>
        <div>
          <label for="work-kind" class="mb-2 block text-xs font-semibold text-dj-muted">Tipo</label>
          <Select v-model="kind" input-id="work-kind" :options="typeOptions" option-label="label" option-value="value" :disabled="busy" class="w-full" pt:root:class="rounded-xl" pt:label:class="py-3" />
        </div>
        <div>
          <label for="work-status" class="mb-2 block text-xs font-semibold text-dj-muted">Situação das demandas</label>
          <Select v-model="status" input-id="work-status" :options="workStatusOptions" option-label="label" option-value="value" :disabled="busy" class="w-full" pt:label:class="py-3" />
        </div>
        <div>
          <label for="work-difficulty" class="mb-2 block text-xs font-semibold text-dj-muted">Dificuldade</label>
          <Select v-model="difficulty" input-id="work-difficulty" :options="['todas', 'Baixa', 'Média', 'Alta'].map(value => ({ value, label: value === 'todas' ? 'Todas as dificuldades' : value }))" option-label="label" option-value="value" :disabled="busy" class="w-full" pt:label:class="py-3" />
        </div>
        <div>
          <label for="work-sort" class="mb-2 block text-xs font-semibold text-dj-muted">Ordenar demandas por</label>
          <Select v-model="sort" input-id="work-sort" :options="[{ value: 'priority', label: 'Maior prioridade' }, { value: 'deadline', label: 'Prazo mais próximo' }, { value: 'newest', label: 'Mais recentes' }]" option-label="label" option-value="value" :disabled="busy" class="w-full" pt:label:class="py-3" />
        </div>
        <div>
          <label for="work-notice-state" class="mb-2 block text-xs font-semibold text-dj-muted">Avisos no mural</label>
          <Select v-model="noticeState" input-id="work-notice-state" :options="noticeStateOptions" option-label="label" option-value="value" :disabled="busy" class="w-full" pt:label:class="py-3" />
        </div>
        <div class="flex flex-wrap gap-2">
          <Button type="submit" label="Buscar" icon="pi pi-search" :disabled="busy" pt:root:class="rounded-xl py-3" />
          <Button type="button" label="Limpar" icon="pi pi-filter-slash" outlined :disabled="busy" pt:root:class="rounded-xl py-3" @click="clearFilters" />
        </div>
      </form>
      <p v-if="board.isFetching.value" role="status" class="mb-4 text-xs text-dj-muted">Atualizando os resultados do quadro…</p>
      <section id="work-results" aria-label="Avisos e grupos por responsável" class="space-y-5">
        <DemandGroup title="Avisos" :total="board.data.value?.notice_total ?? 0" :expanded="noticesExpanded" :disabled="busy"
          :filters="boardFilters" @toggle="noticesExpanded = !noticesExpanded" @open="open" />
        <div>
          <ListHeader id="work-results-title" title="Demandas por responsável"
            :total="!board.isFetching.value ? total : undefined" total-label="Total de demandas"
            description="Expanda os responsáveis para consultar seus projetos, melhorias, erros e atividades." />
          <p v-if="!groups.length" class="rounded-dj-card border border-dashed border-dj-border bg-dj-surface p-6 text-sm text-dj-muted">
            Nenhuma demanda para o responsável selecionado. Cadastre uma demanda ou ajuste o filtro.
          </p>
          <div class="space-y-5">
            <DemandGroup v-for="owner in groups" :key="owner.id" :owner-id="owner.id" :title="owner.name" :total="owner.total"
              :expanded="!collapsed.has(owner.id)" :disabled="busy" :filters="boardFilters"
              @toggle="toggleOwner(owner.id)" @open="open" />
          </div>
        </div>
      </section>
    </RequestState>
    <DemandCreateDialog v-if="creating" :owner-id="ownerId" @closed="createClosed" @busy="busy = $event" @saved="created" @inspect="inspect" />
    <DemandDetail v-if="selectedId" :key="selectedId" :id="selectedId" @closed="detailClosed" @busy="busy = $event"
      @changed="refreshBoard" />
  </section>
</template>
