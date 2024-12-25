import { useAppDispatch, useAppSelector } from "@/app/hooks";
import StepsContainer from "@/components/StepsContainer";
import { step1Tour } from "@/constants";
import { setStep } from "@/data/currentStep";
import { setData } from "@/data/dataSlice";
import { setTourSteps } from "@/data/tour";
import { Company, DataState } from "@/types";
import { Button, Flex, Form, FormProps, Input, Select } from "antd";
import { useEffect, useState } from "react";
import Step2 from "./Step2";
import Step3 from "./Step3";

const Step1 = () => {
  const currentStep = useAppSelector((state) => state.stepReducer.currentStep);

  const steps = [
    {
      id: 0,
      title: __("Company Info"),
      component: <StepOneComponent key={0} />,
    },
    {
      id: 1,
      title: __("Commercial Info"),
      component: <Step2 key={1} />,
      // component: ,
    },
    {
      id: 2,
      title: __("Finishing up"),
      // component: <Step3 />,
      component: <Step3 key={3} />,
    },
  ];

  return (
    <StepsContainer steps={steps}>
      {steps
        .filter((step) => step.id === currentStep)
        .map((step) => step.component)}
    </StepsContainer>
  );
};

const StepOneComponent = () => {
  const dispatch = useAppDispatch();
  const [form] = Form.useForm<DataState>();
  const [companies, setCompanies] = useState<Company[]>([]);
  const dataState = useAppSelector((state) => state.dataReducer);
  const step = useAppSelector((state) => state.stepReducer.currentStep);

  const onFinish: FormProps<DataState>["onFinish"] = (values) => {
    dispatch(setData({ ...values, commercial_register: [], phase: dataState.phase }));
    dispatch(setStep({ currentStep: step + 1 }));
  };

  const onFinishFailed: FormProps<DataState>["onFinishFailed"] = (
    errorInfo
  ) => {
    console.log("FAILED", errorInfo);
  };

  const validateTaxId = (_: unknown, value: string) => {
    if (!value) {
      return Promise.reject(new Error("Tax ID is required!"));
    }
    if (!/^3\d{13}3$/.test(value)) {
      return Promise.reject(
        new Error("Tax ID must start and end with '3' and contain 15 digits!")
      );
    }
    return Promise.resolve(); // Validation passed
  };

  useEffect(() => {
    dispatch(setTourSteps(step1Tour));
  }, []);

  useEffect(() => {
    if (isDev) return;
    const data = frappe.get_list("Company");
    setCompanies(data);
  }, []);

  useEffect(() => {
    if (dataState) {
      form.setFieldsValue({
        company: dataState.company,
        company_name_in_arabic: dataState.company_name_in_arabic,
        tax_id: dataState.tax_id,
      });
    }
  }, []);

  return (
    <Flex flex={1} align="center" className="w-full">
      <Flex align="center" className="w-full" justify="center">
        <Form
          form={form}
          layout="vertical"
          name="basic"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          onFinishFailed={onFinishFailed}
          autoComplete="off"
          size="large"
          className="w-[40%] p-6 mt-5 rounded-md flex flex-col gap-3"
        >
          <Form.Item<DataState>
            name={"company"}
            rules={[{ required: true, message: "Please input your company!" }]}
            className="mb-0"
          >
            <Select
              id="firstInput"
              placeholder={__("Company")}
              options={
                isDev
                  ? [{ value: "company1", label: "company1" }]
                  : companies.map((company) => ({
                      value: company.name,
                      label: company.name,
                    }))
              }
              className="h-12"
            />
          </Form.Item>
          <Form.Item<DataState>
            name={"company_name_in_arabic"}
            className="mb-0"
            rules={[
              {
                required: true,
                message: "Please input your company name in Arabic",
              },
            ]}
          >
            <Input
              id="secondInput"
              placeholder={__("Company name in Arabic")}
              className="h-12"
            />
          </Form.Item>
          <Form.Item<DataState>
            name={"tax_id"}
            rules={[{ validator: validateTaxId }]}
            className="mb-0"
            validateTrigger="onSubmit"
          >
            <Input
              id="thirdInput"
              placeholder={__("TAX ID")}
              className="h-12"
              maxLength={15}
            />
          </Form.Item>
          <Form.Item label={null}>
            <Button
              type="primary"
              className="bg-[#483f61] w-full text-white h-12"
              htmlType="submit"
            >
              {__("Next")}
            </Button>
          </Form.Item>
        </Form>
      </Flex>
    </Flex>
  );
};

export default Step1;
