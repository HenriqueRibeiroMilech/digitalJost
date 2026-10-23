<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import PageHeader from '@/shared/components/PageHeader.vue'
import CardGrid from '@/shared/components/CardGrid.vue'
import RecordCard from '@/shared/components/RecordCard.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import MultiSelect from '@/volt/MultiSelect.vue'
import Tag from '@/volt/Tag.vue'
import DemandDateField from '../components/DemandDateField.vue'
import ManagementCard from '../components/ManagementCard.vue'
import ManagementDetail from '../components/ManagementDetail.vue'
import ManagementCreate from '../components/ManagementCreate.vue'
import ManagementNotice from '../components/ManagementNotice.vue'
import { managementApi } from '../managementApi'
import { demandTypes } from '../managementTypes'
import type { BoardFilters, Notice } from '../managementTypes'
import { displayDate, statusLabel } from '../presentation'
const route = useRoute(); const router = useRouter(); const client = useQueryClient()
const view = computed(() => route.query.view === 'requests' ? 'requests' : 'demands')
const pageElement = ref<HTMLElement | null>(null)
const busy = ref(false); const selected = ref<number | null>(null); const creating = ref(false); const notice = ref<Notice | null>(null)
const modal = computed(() => selected.value !== null || creating.value || notice.value !== null)
watch(() => route.query.demand, value => {
  const id = typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : 0
  if (!busy.value && Number.isSafeInteger(id) && id > 0) selected.value = id
}, { immediate: true })
const initial = (): BoardFilters => ({ search: '', responsible_id: '', demand_type: 'todos', status: '', difficulty: '', sort: 'deadline', completed_from: null, completed_to: null })
const draft = reactive(initial()); const filters = ref(initial()); const statuses = ref<string[]>([]); const initialized = ref(false)
const collapsed = ref(new Set<string>())
const { data: options, isPending: optionsLoading, isError: optionsFailed, error: optionsError, refetch: retryOptions } = useQuery({
  queryKey: ['demands', 'management-options'], queryFn: managementApi.options, retry: false, refetchOnWindowFocus: false,
})
watch(options, value => { if (value && !initialized.value) { draft.completed_to = value.today; filters.value = { ...draft }; initialized.value = true } }, { flush: 'sync' })
const { data: board, isPending, isError, error, refetch } = useQuery({
  queryKey: ['demands', 'management-board', filters], queryFn: () => managementApi.board(filters.value),
  enabled: computed(() => initialized.value && view.value === 'demands'), retry: false,
  refetchInterval: computed(() => modal.value ? false : 60000), refetchIntervalInBackground: false, refetchOnWindowFocus: false,
})
const { data: requests, isPending: requestsLoading, isError: requestsFailed, error: requestsError, refetch: retryRequests } = useQuery({
  queryKey: ['demands', 'management-requests'], queryFn: managementApi.requests,
  enabled: computed(() => initialized.value && view.value === 'requests'), retry: false,
  refetchInterval: computed(() => modal.value ? false : 60000), refetchIntervalInBackground: false, refetchOnWindowFocus: false,
})
const groups = computed(() => {
  const result = new Map<string, { name: string; items: NonNullable<typeof board.value>['items'] }>()
  for (const demand of board.value?.items ?? []) {
    const key = demand.responsible_id ?? 'sem-responsavel'
    if (!result.has(key)) result.set(key, { name: demand.responsible_name ?? 'Responsável indisponível', items: [] })
    result.get(key)!.items.push(demand)
  }
  return Array.from(result.entries()).map(([id, group]) => ({ id, ...group })).sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))
})
const statusOptions = ['a_fazer', 'em_andamento', 'em_validacao', 'pausado', 'aguardando_terceiros', 'aguardando_informacoes', 'concluido'].map(value => ({ value, label: statusLabel(value) }))
onBeforeRouteLeave(() => !busy.value)
onBeforeRouteUpdate(() => !busy.value)
function changeView(value: string) { if (!busy.value) void router.replace({ query: { ...route.query, view: value } }) }
function apply() { filters.value = { ...draft, status: statuses.value.join(',') } }
function reset() { Object.assign(draft, initial(), { completed_to: options.value?.today ?? null }); statuses.value = []; apply() }
function toggle(id: string) { const next = new Set(collapsed.value); if (next.has(id)) next.delete(id); else next.add(id); collapsed.value = next }
async function changed() {
  await Promise.all([client.invalidateQueries({ queryKey: ['demands', 'management-board'] }), client.invalidateQueries({ queryKey: ['demands', 'management-requests'] }),
    client.invalidateQueries({ queryKey: ['demands', 'list'] })])
}
async function closed() {
  const id = selected.value; const noticeId = notice.value?.id
  selected.value = null; notice.value = null; creating.value = false
  if (route.query.demand) {
    const query = { ...route.query }; delete query.demand
    await router.replace({ query })
  }
  await nextTick()
  const target = document.getElementById('managed-open-' + id) ?? document.getElementById('review-open-' + id)
    ?? document.getElementById('notice-open-' + noticeId) ?? document.getElementById('management-create-action') ?? pageElement.value
  target?.focus()
}
</script>
<template>
  <section ref="pageElement" tabindex="-1" aria-labelledby="management-title">
    <PageHeader id="management-title" title="Gestão de demandas" eyebrow="Transformação Digital" description="Organize o trabalho da equipe e analise as novas solicitações.">
      <template #actions><Button id="management-create-action" type="button" label="Nova demanda ou aviso" icon="pi pi-plus" :disabled="!options || optionsFailed || busy || modal" @click="creating = true" /></template>
    </PageHeader>
    <RequestState :loading="optionsLoading" :failed="optionsFailed" :error="optionsError" :empty="false" @retry="retryOptions()">
      <template v-if="options">
        <nav aria-label="Áreas do gerenciador" class="mb-6 flex flex-wrap gap-2">
          <Button type="button" label="Demandas" :outlined="view !== 'demands'" :disabled="busy" :aria-current="view === 'demands' ? 'page' : undefined" @click="changeView('demands')" />
          <Button type="button" label="Solicitações" :outlined="view !== 'requests'" :disabled="busy" :aria-current="view === 'requests' ? 'page' : undefined" @click="changeView('requests')" />
        </nav>
        <section v-if="view === 'demands'" aria-label="Demandas da equipe">
          <form class="mb-5 grid gap-4 rounded-2xl border border-dj-border bg-dj-surface p-4 sm:grid-cols-2 lg:grid-cols-4" @submit.prevent="apply">
            <div><label for="board-search" class="mb-2 block text-sm">Buscar por título ou número</label><InputText id="board-search" v-model="draft.search" :maxlength="250" class="w-full" /></div>
            <div><label for="board-owner" class="mb-2 block text-sm">Responsável</label><Select v-model="draft.responsible_id" input-id="board-owner" :options="[{ id: '', name: 'Todos' }, ...options.responsibles]" option-label="name" option-value="id" filter class="w-full" /></div>
            <div><label for="board-kind" class="mb-2 block text-sm">Tipo</label><Select v-model="draft.demand_type" input-id="board-kind" :options="[{ value: 'todos', label: 'Todos' }, ...demandTypes]" option-label="label" option-value="value" class="w-full" /></div>
            <div><label for="board-status" class="mb-2 block text-sm">Status</label><MultiSelect v-model="statuses" input-id="board-status" :options="statusOptions" option-label="label" option-value="value" placeholder="Todos" class="w-full" /></div>
            <div><label for="board-difficulty" class="mb-2 block text-sm">Dificuldade</label><Select v-model="draft.difficulty" input-id="board-difficulty" :options="[{ value: '', label: 'Todas' }, ...['Baixa', 'Média', 'Alta'].map(value => ({ value, label: value }))]" option-label="label" option-value="value" class="w-full" /></div>
            <div><label for="board-sort" class="mb-2 block text-sm">Ordenar por</label><Select v-model="draft.sort" input-id="board-sort" :options="[{ value: 'deadline', label: 'Prazo mais próximo' }, { value: 'priority', label: 'Maior prioridade' }]" option-label="label" option-value="value" class="w-full" /></div>
            <DemandDateField id="completed-from" v-model="draft.completed_from" label="Conclusões a partir de" />
            <DemandDateField id="completed-to" v-model="draft.completed_to" label="Conclusões até" />
            <p class="text-xs leading-5 text-dj-muted sm:col-span-2 lg:col-span-4">As demandas ativas continuam incluídas. Ao informar o início, o período acrescenta as concluídas entre as duas datas, inclusive.</p>
            <div class="flex gap-2 sm:col-span-2 lg:col-span-4"><Button type="submit" label="Aplicar filtros" /><SecondaryButton type="button" label="Restaurar padrão" outlined @click="reset" /></div>
          </form>
          <RequestState :loading="isPending" :failed="isError" :error="error" :empty="board?.items.length === 0 && board?.notices.length === 0" empty-title="Nenhuma demanda para estes filtros"
            empty-description="Altere os filtros ou cadastre uma demanda ou aviso." @retry="refetch()">
            <section v-if="board?.notices.length" class="mb-8" aria-label="Avisos">
              <h2 class="mb-4 text-lg font-semibold">Avisos</h2><CardGrid>
                <RecordCard v-for="item in board.notices" :key="item.id" :title-id="'notice-title-' + item.id" :title="item.title" :description="item.description"
                  :action-id="'notice-open-' + item.id" icon="pi pi-megaphone" action-label="Ver aviso" compact opens-dialog tone="neutral" @open="notice = item">
                  <template #badge><Tag value="Aviso" severity="secondary" /></template>
                  <p class="text-xs text-dj-muted">{{ item.created_by_name ?? 'Equipe' }}</p>
                </RecordCard>
              </CardGrid>
            </section>
            <section v-for="group in groups" :key="group.id" class="mb-8">
              <button type="button" class="mb-4 flex w-full items-center justify-between gap-3 rounded-xl border border-dj-border bg-dj-surface p-4 text-left" :aria-expanded="!collapsed.has(group.id)" @click="toggle(group.id)">
                <span class="font-semibold">{{ group.name }}</span><span class="text-xs text-dj-muted">{{ group.items.length }} demanda(s) · {{ group.items.filter(item => item.status !== 'concluido').length }} ativa(s)</span>
              </button>
              <CardGrid v-show="!collapsed.has(group.id)"><ManagementCard v-for="item in group.items" :key="item.id" :demand="item" :today="board?.today ?? options.today" @open="selected = item.id" /></CardGrid>
            </section>
          </RequestState>
        </section>
        <section v-else aria-label="Solicitações abertas">
          <RequestState :loading="requestsLoading" :failed="requestsFailed" :error="requestsError" :empty="requests?.items.length === 0" empty-title="Nenhuma solicitação aberta"
            empty-description="Novas solicitações e pedidos aguardando informações aparecem aqui." @retry="retryRequests()">
            <CardGrid><RecordCard v-for="item in requests?.items ?? []" :key="item.id" :title-id="'review-title-' + item.id" :title="item.title" :description="item.description"
              :action-id="'review-open-' + item.id" action-label="Analisar solicitação" opens-dialog compact @open="selected = item.id">
              <template #marker><span class="text-xs font-semibold">#{{ item.id }} · {{ item.entry_kind === 'erro' ? 'Erro' : 'Solicitação' }}</span></template>
              <template #badge><Tag :value="statusLabel(item.status)" severity="secondary" /></template>
              <p class="text-xs text-dj-muted">{{ item.requester_name ?? 'Solicitante' }} · Urgência {{ item.urgency }}</p>
              <p class="mt-2 text-xs text-dj-muted">{{ displayDate(item.created_at) }}</p>
            </RecordCard></CardGrid>
          </RequestState>
        </section>
      </template>
    </RequestState>
    <ManagementDetail v-if="selected && options" :key="selected" :id="selected" :options="options" @closed="closed" @changed="changed" @busy="busy = $event" />
    <ManagementCreate v-if="creating && options" :options="options" @closed="closed" @saved="changed" @busy="busy = $event" />
    <ManagementNotice v-if="notice" :notice="notice" @closed="closed" @saved="changed" @busy="busy = $event" />
  </section>
</template>
