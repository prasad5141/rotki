<script setup lang="ts">
import { TimeUnit } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePersist,
  type TimeFrameSetting,
  timeframes
} from '@rotki/common/lib/settings/graphs';
import dayjs from 'dayjs';
import { Section } from '@/types/status';

const { t } = useI18n();
const { currencySymbol, floatingPrecision } = storeToRefs(
  useGeneralSettingsStore()
);
const sessionStore = useSessionSettingsStore();
const { update } = sessionStore;
const { timeframe } = storeToRefs(sessionStore);
const { premium } = storeToRefs(usePremiumStore());
const statistics = useStatisticsStore();
const { fetchNetValue, getNetValue } = statistics;
const { totalNetWorth } = storeToRefs(statistics);
const frontendStore = useFrontendSettingsStore();
const { visibleTimeframes } = storeToRefs(frontendStore);

const { isLoading: isSectionLoading } = useStatusStore();

const isLoading = logicOr(
  isSectionLoading(Section.BLOCKCHAIN_ETH),
  isSectionLoading(Section.BLOCKCHAIN_BTC)
);

const startingValue = computed(() => {
  const data = get(timeframeData).data;
  let start = data[0];
  if (start === 0) {
    for (let i = 1; i < data.length; i++) {
      if (data[i] > 0) {
        start = data[i];
        break;
      }
    }
  }
  return bigNumberify(start);
});

const adjustedTotalNetWorthFontSize = computed(() => {
  const digits = get(totalNetWorth)
    .toFormat(get(floatingPrecision))
    .replace(/\./g, '')
    .replace(/,/g, '').length;

  // this number adjusted visually
  // when we use max floating precision (8), it won't overlap
  return Math.min(1, 12 / digits);
});

const allTimeframes = computed(() =>
  timeframes((unit, amount) =>
    dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
  )
);

const balanceDelta = computed(() =>
  get(totalNetWorth).minus(get(startingValue))
);

const timeframeData = computed(() => {
  const all = get(allTimeframes);
  const selection = get(timeframe);
  const startingDate = all[selection].startingDate();
  return get(getNetValue(startingDate));
});

const percentage = computed(() => {
  const bigNumber = get(balanceDelta).div(get(startingValue)).multipliedBy(100);

  return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
});

const indicator = computed(() => {
  if (get(isLoading)) {
    return '';
  }
  return get(balanceDelta).isNegative() ? 'mdi-menu-down' : 'mdi-menu-up';
});

const balanceClass = computed(() => {
  if (get(isLoading)) {
    return 'rotki-grey lighten-3';
  }
  return get(balanceDelta).isNegative() ? 'rotki-red lighten-1' : 'rotki-green';
});

const setTimeframe = async (value: TimeFrameSetting) => {
  assert(value !== TimeFramePersist.REMEMBER);
  sessionStore.update({ timeframe: value });
  await frontendStore.updateSetting({ lastKnownTimeframe: value });
};

const { logged } = storeToRefs(useSessionAuthStore());

watch(premium, async () => {
  if (get(logged)) {
    await fetchNetValue();
  }
});

onMounted(() => {
  const isPremium = get(premium);
  const selectedTimeframe = get(timeframe);
  if (!isPremium && !isPeriodAllowed(selectedTimeframe)) {
    update({ timeframe: TimeFramePeriod.TWO_WEEKS });
  }
});

const { showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());
const chartSectionHeight = computed<string>(() => {
  const height = 208 + (get(showGraphRangeSelector) ? 60 : 0);
  return `${height}px`;
});
</script>

<template>
  <VCard class="overall-balances">
    <VRow no-gutters class="pa-5">
      <VCol
        cols="12"
        md="6"
        lg="5"
        class="d-flex flex-column align-center justify-center"
      >
        <div
          class="overall-balances__net-worth text-center font-weight-medium mb-2"
        >
          <div :style="`font-size: ${adjustedTotalNetWorthFontSize}em`">
            <AmountDisplay
              class="ps-4"
              xl
              show-currency="symbol"
              :fiat-currency="currencySymbol"
              :value="totalNetWorth"
            />
          </div>
        </div>
        <div class="overall-balances__net-worth-change py-2">
          <span
            :class="balanceClass"
            class="pa-1 px-2 overall-balances__net-worth-change__pill"
          >
            <Loading
              v-if="isLoading"
              class="overall-balances__net-worth__loading d-flex justify-center mt-n2"
            />
            <span v-else class="d-flex flex-row">
              <span class="me-2">
                <VIcon>{{ indicator }}</VIcon>
              </span>
              <AmountDisplay
                v-if="!isLoading"
                show-currency="symbol"
                :fiat-currency="currencySymbol"
                :value="balanceDelta"
              />
              <PercentageDisplay
                v-if="!isLoading"
                class="ms-2 px-1 text--secondary pe-2"
                :value="percentage"
              />
            </span>
          </span>
        </div>
        <TimeframeSelector
          :value="timeframe"
          :visible-timeframes="visibleTimeframes"
          @input="setTimeframe($event)"
        />
      </VCol>
      <VCol cols="12" md="6" lg="7" class="d-flex">
        <div
          class="d-flex justify-center align-center flex-grow-1 overall-balances__net-worth-chart"
        >
          <NetWorthChart
            v-if="!isLoading"
            :chart-data="timeframeData"
            :timeframe="timeframe"
            :timeframes="allTimeframes"
          />
          <div v-else class="overall-balances__net-worth-chart__loader">
            <VProgressCircular
              indeterminate
              class="align-self-center"
              color="primary"
            />
            <div class="pt-5 text-caption">
              {{ t('overall_balances.loading') }}
            </div>
          </div>
        </div>
      </VCol>
    </VRow>
  </VCard>
</template>

<style scoped lang="scss">
.overall-balances {
  &__balance {
    display: flex;
    justify-content: center;
    align-items: baseline;
  }

  &__net-worth {
    &__loading {
      font-size: 1.5em;
      line-height: 1em;
      margin-bottom: -10px;
    }
  }

  &__net-worth-change {
    display: flex;
    justify-content: center;
    align-items: baseline;
    margin-bottom: 1em;
    min-height: 32px;

    span {
      border-radius: 0.75em;
    }

    &__pill {
      min-height: 32px;
      min-width: 170px;
    }
  }

  &__net-worth-chart {
    width: 100%;

    &__loader {
      min-height: v-bind(chartSectionHeight);
      display: flex;
      height: 100%;
      flex-direction: column;
      align-content: center;
      justify-content: center;
      text-align: center;
    }
  }
}
</style>
