import { useAppDispatch, useAppSelector } from "@/app/hooks";
import StepsContainer from "@/components/StepsContainer";
import { setStep } from "@/data/currentStep";
import { setData } from "@/data/dataSlice";
import { Company, DataState } from "@/types";
import { Button, Flex, Form, FormProps, Input, Select } from "antd";
import { useState } from "react";
import Step2 from "./Step2";
import Step3 from "./Step3";


const Step1 = () => {
  const currentStep = useAppSelector((state) => state.stepReducer.currentStep);

  const steps = [
    {
      id: 0,
      title: "Company Info",
      component: <StepOneComponent />,
    },
    {
      id: 1,
      title: "Commercial Info",
      component: <Step2 />,
      // component: ,
    },
    {
      id: 2,
      title: "Finishing up",
      // component: <Step3 />,
      component: <Step3 />,
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
  const step = useAppSelector((state) => state.stepReducer.currentStep);

  const onFinish: FormProps<DataState>["onFinish"] = (values) => {
    console.log("Received values of form:", values);
    dispatch(setData({...values, commercial_register: []}))
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

  return (
    <Flex flex={1} align="center" className="w-full">
      <Flex align="center" className="w-full" justify="center" >
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
              placeholder="Company"
              options={[{ value: "company1", label: "company1" }]}
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
            <Input placeholder="Company name in Arabic" className="h-12" />
          </Form.Item>
          <Form.Item<DataState>
            name={"tax_id"}
            rules={[{ validator: validateTaxId }]}
            className="mb-0"
            validateTrigger="onSubmit"
          >
            <Input placeholder="TAX ID" className="h-12" maxLength={15} />
          </Form.Item>
          <Form.Item label={null}>
            <Button
              type="primary"
              className="bg-[#483f61] w-full text-white h-12"
              htmlType="submit"
            >
              Next
            </Button>
          </Form.Item>
        </Form>
      </Flex>
    </Flex>
  );
};

export default Step1;
