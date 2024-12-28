import { useAppDispatch, useAppSelector } from "@/app/hooks";
import {
  generateCommercials,
  LHSinputs,
  RHSinputs,
  top_inputs,
} from "@/constants";
import { setStep } from "@/data/currentStep";
import { addCommercial } from "@/data/dataSlice";
import { deactivateEdit } from "@/data/editModal";
import { setTourSteps } from "@/data/tour";
import { CommercialData } from "@/types";
import { CheckCircleFilled } from "@ant-design/icons";
import {
  Button,
  Collapse,
  CollapseProps,
  Descriptions,
  Flex,
  Form,
  FormProps,
  Input,
  Typography,
} from "antd";
import React, { useEffect } from "react";

interface Props {
  commercial?: CommercialData;
  edit?: boolean;
}

const Step2: React.FC<Props> = ({ edit, commercial }) => {
  const [form] = Form.useForm();
  const dispatch = useAppDispatch();
  const comName = Form.useWatch("commercial_register_name", form);
  const comNo = Form.useWatch("commercial_register_number", form);
  const currentStep = useAppSelector((state) => state.stepReducer.currentStep);
  const dataState = useAppSelector((state) => state.dataReducer);
  const commission = useAppSelector(
    (state) => state.commissionReducer.commission
  );
  const isAdding = useAppSelector((state) => state.addingReducer.isAdding);

  const step2Tour = [
    {
      title: __("Commercial Register Name"),
      description: __("Put your commercial register name here"),
      // cover: (
      //   <img
      //     alt="tour.png"
      //     src="https://user-images.githubusercontent.com/5378891/197385811-55df8480-7ff4-44bd-9d43-a7dade598d70.png"
      //   />
      // ),
      target: "commercial_register_name",
    },
    {
      title: __("Commercial Register Number"),
      description: __("Commercial Register Number here"),
      target: "commercial_register_number",
    },
    commission === "multi" && {
      title: __("Commission List"),
      description: __("In here u will see all ur branches"),
      target: "commission_list",
    },
  ].filter(Boolean);

  const items: CollapseProps["items"] = [
    ...dataState.commercial_register.flatMap((c, index) => ({
      key: index,
      label: c.commercial_register_name,
      children: (
        <Descriptions bordered size="small">
          <Descriptions.Item span={3} label={__("Commercial Name")}>
            {c.commercial_register_name}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("Commercial Number")}>
            {c.commercial_register_number}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("Short Address")}>
            {c.short_address}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("Building No")}>
            {c.building_no}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("Street")}>
            {c.address_line1}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("Secondary No")}>
            {c.address_line2}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("City")}>
            {c.city}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("District")}>
            {c.district}
          </Descriptions.Item>
          <Descriptions.Item span={3} label={__("Postal Code")}>
            {c.pincode}
          </Descriptions.Item>
          {c.more_info ? (
            <Descriptions.Item span={3} label={__("More Info")}>
              {c.more_info}
            </Descriptions.Item>
          ) : null}
        </Descriptions>
      ),
    })),
  ];

  const isValid = () => {
    if (comName && comNo && comNo.length === 10) return true;
    return false;
  };

  const onFinish: FormProps<CommercialData>["onFinish"] = (values) => {
    dispatch(addCommercial(values));
    if (edit && commercial) {
      dispatch(deactivateEdit());
      return;
    }
    if (commission === "multi" || isAdding) {
      form.resetFields();
      return;
    }
    nextStep();
  };

  const nextStep = () => {
    dispatch(setStep({ currentStep: currentStep + 1 }));
  };

  useEffect(() => {
    if (commercial) {
      form.setFieldsValue(commercial);
    }

    if (isDev) {
      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.ctrlKey && event.key === "v") {
          const commercials = generateCommercials();
          commercials.map((c) => {
            dispatch(addCommercial(c));
          });
        }
      };

      addEventListener("keydown", handleKeyDown);

      return () => {
        removeEventListener("keydown", handleKeyDown);
      };
    }
  }, []);

  useEffect(() => {
    dispatch(setTourSteps(step2Tour));
  }, []);

  return (
    <Flex flex={1} align="center" justify="center">
      {(commission === "multi" && !edit) || isAdding ? (
        <div
          id="commission_list"
          className="bg-[#00000027] rounded-md h-[600px] overflow-y-auto w-[350px]"
        >
          <Collapse accordion items={items} ghost className=" bg-[#483f61]" />
        </div>
      ) : null}
      <Flex flex={1} className="h-full" align="center" justify="center">
        <Flex
          align={edit ? "start" : "center"}
          justify="center"
          className="w-full"
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{ remember: true }}
            onFinish={onFinish}
            autoComplete="off"
            size="large"
            className={`${
              edit
                ? "w-[100%]"
                : commission === "multi" || isAdding
                ? "w-[60%]"
                : "w-[40%]"
            }  p-6 ${!edit && "mt-5"} rounded-md h-full flex flex-col gap-3`}
          >
            {isValid() ? (
              <Typography.Text className="text-lg self-center">
                Commercial Information &nbsp;{" "}
                <CheckCircleFilled className="text-green-700" />
              </Typography.Text>
            ) : null}
            {top_inputs.map((i) => (
              <Form.Item<CommercialData>
                key={i.id}
                name={i.id as keyof CommercialData}
                className="mb-0"
                rules={i.rules}
                validateTrigger="onSubmit"
              >
                <Input
                  id={i.id}
                  placeholder={i.name}
                  maxLength={i.maxlength ?? undefined}
                  disabled={edit ? i.disabled : false}
                />
              </Form.Item>
            ))}
            {isValid() ? (
              <>
                <Typography.Text className="text-lg self-center">
                  {__("Saudi National Address Components")}
                </Typography.Text>
                <Flex gap={5}>
                  {/* Left Side */}
                  <Flex vertical className="w-full" gap={5}>
                    {LHSinputs.map((i) => (
                      <Form.Item<CommercialData>
                        key={i.id}
                        name={i.id as keyof CommercialData}
                        rules={i.rules}
                        className="mb-0"
                        validateTrigger="onSubmit"
                      >
                        <Input
                          placeholder={i.name}
                          maxLength={i.maxlength ?? undefined}
                        />
                      </Form.Item>
                    ))}
                  </Flex>
                  {/* Right side */}
                  <Flex vertical className="w-full" gap={5}>
                    {RHSinputs.map((i) => (
                      <Form.Item<CommercialData>
                        key={i.id}
                        name={i.id as keyof CommercialData}
                        rules={i.rules}
                        className="mb-0"
                        validateTrigger="onSubmit"
                      >
                        <Input
                          placeholder={i.name}
                          maxLength={i.maxlength ?? undefined}
                        />
                      </Form.Item>
                    ))}
                  </Flex>
                </Flex>
              </>
            ) : null}

            <Form.Item>
              <Button
                type="primary"
                className="bg-[#483f61] w-full disabled:opacity-90 disabled:text-white"
                htmlType="submit"
              >
                {edit
                  ? __("Edit")
                  : commission === "multi" || isAdding
                  ? __("Add")
                  : __("Next")}
              </Button>
            </Form.Item>
          </Form>
        </Flex>
      </Flex>
      {(!edit && commission === "multi") || isAdding ? (
        <Button
          onClick={nextStep}
          disabled={!dataState.commercial_register.length}
          className="mt-auto p-5 m-2 bg-[#483f61] text-white disabled:opacity-85"
        >
          {__("Next")}
        </Button>
      ) : null}
    </Flex>
  );
};

export default Step2;
