import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { addOTP } from "@/data/dataSlice";
import { CommercialData } from "@/types";
import { Flex, Input, Modal, Typography } from "antd";
import React, { useState } from "react";

interface Props {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const OTPModal: React.FC<Props> = ({ open, setOpen }) => {
  const dispatch = useAppDispatch();
  let dataState = useAppSelector((state) => state.dataReducer);

  const [otpValues, setOtpValues] = useState({});
  const [otpLoading, setOtpLoading] = useState<boolean>(false);

  const handleOtpChange = (value: string, commercial: CommercialData) => {
    setOtpValues((prev) => ({
      ...prev,
      [commercial.commercial_register_number]: value,
    }));
  };

  const handleSubmit = (otpValues: any) => {
    setOtpLoading(true);
    dispatch(addOTP(otpValues));
    dispatch(setCurrentPage(204));
    setOtpLoading(false);
  };

  return (
    <>
      <Modal
        centered
        title={__("Please provide an OTP")}
        open={open}
        onOk={() => handleSubmit(otpValues)}
        confirmLoading={otpLoading}
        onCancel={() => setOpen(false)}
        className="w-[35%]"
        okText={__("Confirm")}
        cancelText={__("Cancel")}
        okButtonProps={{
          className: "bg-[#39b54a] text-white disabled:opacity-50",
          disabled:
            Object.keys(otpValues).length <
            dataState.commercial_register.filter((c) => !c.phase).length,
        }}
      >
        <Flex gap="middle" align="center" vertical className="p-5">
          {dataState.commercial_register
            .filter((c) => !c.phase)
            .map((com, index) => (
              <Flex
                key={index}
                align="center"
                justify="space-between"
                className="w-full"
              >
                {!com.otp ? (
                  <>
                    <Typography.Text className="text-lg">
                      {com.commercial_register_name}
                    </Typography.Text>
                    <div>
                      <Input.OTP
                        key={index}
                        formatter={(str) => str.toUpperCase()}
                        onChange={(e) => handleOtpChange(e, com)}
                      />
                    </div>
                  </>
                ) : null}
              </Flex>
            ))}
        </Flex>
      </Modal>
    </>
  );
};

export default OTPModal;
