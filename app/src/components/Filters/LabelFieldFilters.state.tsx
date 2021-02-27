import { atomFamily, selector, selectorFamily } from "recoil";

import { Range } from "./RangeSlider";
import { isBooleanField, isNumericField, isStringField } from "./utils";
import * as booleanField from "./BooleanFieldFilter";
import * as numericField from "./NumericFieldFilter";
import * as stringField from "./StringFieldFilter";
import * as atoms from "../../recoil/atoms";
import * as selectors from "../../recoil/selectors";
import { RESERVED_FIELDS, VALID_LIST_TYPES } from "../../utils/labels";

export const modalFilterIncludeLabels = atomFamily<string[], string>({
  key: "modalFilterIncludeLabels",
  default: [],
});

export const modalFilterLabelConfidenceRange = atomFamily<Range, string>({
  key: "modalFilterLabelConfidenceRange",
  default: [null, null],
});

export const modalFilterLabelIncludeNoConfidence = atomFamily<boolean, string>({
  key: "modalFilterLabelIncludeNoConfidence",
  default: true,
});

interface Label {
  confidence?: number;
  label?: number;
}

type LabelFilters = {
  [key: string]: (label: Label) => boolean;
};

export const getPathExtension = (type: string): string => {
  if (VALID_LIST_TYPES.includes(type)) {
    return `.${type.toLocaleLowerCase()}`;
  }
  return "";
};

export const labelFilters = selectorFamily<LabelFilters, boolean>({
  key: "labelFilters",
  get: (modal) => ({ get }) => {
    const activeLabels = modal ? atoms.modalActiveLabels : atoms.activeLabels;
    const frameLabels = activeLabels("frame");
    const labels = {
      ...get(activeLabels("sample")),
      ...Object.keys(get(frameLabels)).reduce((acc, cur) => {
        return {
          ...acc,
          ["frames." + cur]: frameLabels[cur],
        };
      }, {}),
    };
    const filters = {};
    const typeMap = get(selectors.labelTypesMap);
    const hiddenObjects = modal ? get(atoms.hiddenObjects) : null;
    for (const label in labels) {
      const path = `${label}${getPathExtension(typeMap[label])}`;

      const [cRangeAtom, cNoneAtom, lValuesAtom, lExcludeAtom] = modal
        ? [
            numericField.rangeModalAtom,
            numericField.noneModalAtom,
            stringField.selectedValuesModalAtom,
            stringField.excludeModalAtom,
          ]
        : [
            numericField.rangeAtom,
            numericField.noneAtom,
            stringField.selectedValuesAtom,
            stringField.excludeAtom,
          ];

      const cPath = `${path}.confidence`;
      const lPath = `${path}.label`;

      const [cRange, cNone, lValues, lExclude] = [
        get(cRangeAtom({ path: cPath, defaultRange: [0, 1] })),
        get(cNoneAtom({ path: cPath, defaultRange: [0, 1] })),
        get(lValuesAtom(lPath)),
        get(lExcludeAtom(lPath)),
      ];

      filters[label] = (s) => {
        if (hiddenObjects && hiddenObjects[s.id]) {
          return false;
        }
        const inRange =
          cRange[0] - 0.005 <= s.confidence &&
          s.confidence <= cRange[1] + 0.005;
        const noConfidence = cNone && s.confidence === undefined;
        let label = s.label ? s.label : s.value;
        if (label === undefined) {
          label = null;
        }
        let included = lValues.includes(label);
        if (lExclude) {
          included = !included;
        }
        return (inRange || noConfidence) && (included || lValues.length === 0);
      };
    }
    return filters;
  },
  set: () => ({ get, set }, _) => {
    const paths = get(selectors.labelTypesMap);
    const activeLabels = get(atoms.activeLabels("sample"));
    set(atoms.modalActiveLabels("sample"), activeLabels);
    const activeFrameLabels = get(atoms.activeLabels("frame"));
    set(atoms.modalActiveLabels("frame"), activeFrameLabels);
    for (const [label, type] of Object.entries(paths)) {
      const path = `${label}${getPathExtension(type)}`;
      const cPath = `${path}.confidence`;
      const lPath = `${path}.label`;
      set(
        numericField.rangeModalAtom({ path: cPath, defaultRange: [0, 1] }),
        get(numericField.rangeAtom({ path: cPath, defaultRange: [0, 1] }))
      );

      set(
        numericField.noneModalAtom({ path: cPath, defaultRange: [0, 1] }),
        get(numericField.noneModalAtom({ path: cPath, defaultRange: [0, 1] }))
      );

      set(
        stringField.selectedValuesModalAtom(lPath),
        get(stringField.selectedValuesAtom(lPath))
      );

      set(
        stringField.excludeModalAtom(lPath),
        get(stringField.excludeAtom(lPath))
      );

      set(atoms.modalColorByLabel, get(atoms.colorByLabel));
    }
  },
});

export const sampleModalFilter = selector({
  key: "sampleModalFilter",
  get: ({ get }) => {
    const filters = get(labelFilters(true));
    const frameLabels = get(atoms.modalActiveLabels("frame"));
    const activeLabels = {
      ...get(atoms.modalActiveLabels("sample")),
      ...Object.keys(frameLabels).reduce((acc, cur) => {
        return {
          ...acc,
          ["frames." + cur]: frameLabels[cur],
        };
      }, {}),
    };
    const hiddenObjects = get(atoms.hiddenObjects);

    return (sample) => {
      return Object.entries(sample).reduce((acc, [key, value]) => {
        if (value && hiddenObjects[value.id]) {
          return acc;
        }
        if (key === "tags") {
          acc[key] = value;
        } else if (value && VALID_LIST_TYPES.includes(value._cls)) {
          if (activeLabels[key]) {
            acc[key] =
              filters[key] && value !== null
                ? {
                    ...value,
                    [value._cls.toLowerCase()]: value[
                      value._cls.toLowerCase()
                    ].filter((l) => filters[key](l) && !hiddenObjects[l.id]),
                  }
                : value;
          }
        } else if (value !== null && filters[key] && filters[key](value)) {
          acc[key] = value;
        } else if (RESERVED_FIELDS.includes(key)) {
          acc[key] = value;
        } else if (
          ["string", "number", "null"].includes(typeof value) &&
          activeLabels[key]
        ) {
          acc[key] = value;
        }
        return acc;
      }, {});
    };
  },
});

export const fieldIsFiltered = selectorFamily<
  boolean,
  { path: string; modal: boolean }
>({
  key: "fieldIsFiltered",
  get: ({ path, modal }) => ({ get }) => {
    const isArgs = { path, modal };
    if (get(isBooleanField(path))) {
      return get(booleanField.fieldIsFiltered(isArgs));
    } else if (get(isNumericField(path))) {
      return get(numericField.fieldIsFiltered(isArgs));
    } else if (get(isStringField(path))) {
      return get(stringField.fieldIsFiltered(isArgs));
    }

    path = `${path}${getPathExtension(get(selectors.labelTypesMap)[path])}`;
    const cPath = `${path}.confidence`;
    const lPath = `${path}.label`;

    return (
      get(
        numericField.fieldIsFiltered({
          ...isArgs,
          path: cPath,
          defaultRange: [0, 1],
        })
      ) || get(stringField.fieldIsFiltered({ ...isArgs, path: lPath }))
    );
  },
});
