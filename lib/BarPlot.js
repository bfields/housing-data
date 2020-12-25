import { fieldsGenerator } from '../lib/plots.js'
import ContainerDimensions from 'react-container-dimensions'
import { VegaLite } from 'react-vega'

const unitsLabels = {
  units: 'Units permitted',
  bldgs: 'Housing buildings permitted',
  value: 'Property value of permitted buildings'
}

const baseKeyMapping = {
  '1_unit_units': '1 unit',
  '2_units_units': '2 units',
  '3_to_4_units_units': '3-4 units',
  '5_plus_units_units': '5+ units',
  '1_unit_bldgs': '1 unit',
  '2_units_bldgs': '2 units',
  '3_to_4_units_bldgs': '3-4 units',
  '5_plus_units_bldgs': '5+ units',
  '1_unit_value': '1 unit',
  '2_units_value': '2 units',
  '3_to_4_units_value': '3-4 units',
  '5_plus_units_value': '5+ units'
}

export const keyMapping = {}
for (const [key, value] of Object.entries(baseKeyMapping)) {
  keyMapping[key] = value
  keyMapping[key + '_per_capita'] = value
}

const fields = Array.from(fieldsGenerator())

export default function BarPlot ({ data, units, perCapita }) {
  return (
    <ContainerDimensions>
      {({ width, height }) => (
        <VegaLite spec={makeSpec(units, perCapita, width, height)} data={data} />
      )}
    </ContainerDimensions>
  )
}

function makeSpec (units, perCapita, width, height) {
  const perCapitaSuffix = perCapita ? '_per_capita' : ''
  const filterFields = Array.from(fieldsGenerator([units], [''], [perCapitaSuffix]))

  const plotWidth = Math.min(width * 0.95, 936)
  const continuousBandSize = plotWidth * 10 / 936

  const suffix = perCapita ? '_per_capita' : ''

  const yLabel = unitsLabels[units]
  const yTitle = perCapita ? yLabel + ' per capita' : yLabel

  const yFormat = units === 'value' ? (perCapita ? '$.2f' : '$s') : null

  return {
    width: plotWidth,
    height: 0.75 * plotWidth,
    autosize: {
      type: 'fit',
      contains: 'padding'
    },
    encoding: {
      x: {
        field: 'year',
        type: 'temporal',
        axis: { title: 'Year' }
      },
      y: { field: 'value', type: 'quantitative', axis: { title: yTitle, format: yFormat } },
      color: { field: 'key', type: 'nominal', axis: { title: 'Unit count' } }
    },
    scales: [
      {
        name: 'legend_labels',
        type: 'nominal',
        domain: ['1_unit_units' + suffix, '2_units_units' + suffix, '3_to_4_units_units' + suffix, '5_plus_units_units' + suffix],
        range: ['1 unit', '2 units', '3-4 units', '5+ units']
      }
    ],
    transform: [
      { fold: fields },
      {
        filter: {
          field: 'key',
          oneOf: filterFields
        }
      },
      {
        calculate: JSON.stringify(keyMapping) + '[datum.key] || "Error"',
        as: 'key_pretty_printed'
      }
    ],
    data: { name: 'table' }, // note: vega-lite data attribute is a plain object instead of an array
    usermeta: { embedOptions: { renderer: 'svg' } },
    layer: [
      {
        mark: {
          type: 'bar',
          tooltip: { content: 'data' }
        },
        encoding: {
          x: {
            field: 'year'
          },
          y: {
            field: 'value'
          },
          color: {
            field: 'key_pretty_printed',
            scale: {
              scheme: 'tableau10'
            }
          },
          tooltip: [
            { field: 'year', type: 'temporal', scale: { type: 'utc' }, timeUnit: 'utcyear', title: 'Year' },
            { field: '1_unit_units', title: '1 unit', format: ',' },
            { field: '2_units_units', title: '2 units', format: ',' },
            { field: '3_to_4_units_units', title: '3-4 units', format: ',' },
            { field: '5_plus_units_units', title: '5+ units', format: ',' },
            { field: 'total_units', title: 'Total units', format: ',' }
          ]
        },
        tooltip: true
      }
    ],
    config: {
      bar: {
        continuousBandSize: continuousBandSize
      }
      // axis: {labelFont: "sans-serif", titleFont: "sans-serif"},
      // legend: {labelFont: "sans-serif", titleFont: "sans-serif"},
      // header: {labelFont: "sans-serif", titleFont: "sans-serif"},
      // mark: {font: "sans-serif"},
      // title: {font: "sans-serif", subtitleFont: "sans-serif"},
    }
  }
}